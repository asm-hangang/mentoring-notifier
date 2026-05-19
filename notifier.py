import os
import json
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.swmaestro.ai"
LOGIN_PAGE = f"{BASE_URL}/sw/member/user/forLogin.do?menuNo=200025"
LOGIN_POST = f"{BASE_URL}/sw/member/user/toLogin.do"
LIST_URL = f"{BASE_URL}/sw/mypage/mentoLec/list.do?menuNo=200046"
STATE_FILE = "last_seen.json"


def login(session: requests.Session, username: str, password: str) -> bool:
    r = session.get(LOGIN_PAGE)
    soup = BeautifulSoup(r.text, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfToken"})
    if not csrf_input:
        raise RuntimeError("CSRF token not found on login page")

    session.post(LOGIN_POST, data={
        "loginFlag": "",
        "menuNo": "200025",
        "csrfToken": csrf_input["value"],
        "username": username,
        "password": password,
    })

    # 로그인 성공 여부: 목록 페이지 접근 후 로그인 페이지로 리다이렉트되지 않으면 성공
    check = session.get(LIST_URL, allow_redirects=False)
    return check.status_code == 200


def fetch_items(session: requests.Session) -> list[dict]:
    r = session.get(LIST_URL)
    soup = BeautifulSoup(r.text, "html.parser")

    # 제목 컬럼이 있는 테이블을 찾음
    target_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "제목" in headers and "NO." in headers:
            target_table = table
            break

    if not target_table:
        return []

    headers = [th.get_text(strip=True) for th in target_table.find_all("th")]
    items = []
    for tr in target_table.find_all("tr")[1:]:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cells) < len(headers):
            continue
        row = dict(zip(headers, cells))
        try:
            row["_no"] = int(row.get("NO.", "0"))
        except ValueError:
            continue
        items.append(row)

    return items


def send_slack(webhook_url: str, new_items: list[dict]) -> None:
    lines = [f"*새로운 멘토링/특강 {len(new_items)}개 등록됨!*"]
    for item in new_items:
        lines.append(
            f"• [{item.get('NO.', '')}] *{item.get('제목', '')}*\n"
            f"  📅 진행: {item.get('진행날짜', '')}\n"
            f"  ⏰ 접수: {item.get('접수기간', '')}\n"
            f"  👥 모집인원: {item.get('모집인원', '')}  |  {item.get('상태', '')}"
        )
    lines.append(f"\n<{LIST_URL}|멘토링 목록 보기>")
    requests.post(webhook_url, json={"text": "\n".join(lines)}, timeout=10)


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_no": 0}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main() -> None:
    username = os.environ["SW_USERNAME"]
    password = os.environ["SW_PASSWORD"]
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    if not login(session, username, password):
        raise RuntimeError("Login failed — check SW_USERNAME / SW_PASSWORD")

    items = fetch_items(session)
    if not items:
        print("No items found (parse error or empty list)")
        return

    state = load_state()
    last_no = state["last_no"]

    new_items = [i for i in items if i["_no"] > last_no]

    if new_items:
        send_slack(webhook_url, new_items)
        print(f"Notified: {len(new_items)} new item(s)")
    else:
        print("No new items")

    max_no = max(i["_no"] for i in items)
    if max_no > last_no:
        save_state({"last_no": max_no})
        print(f"State updated: last_no={max_no}")


if __name__ == "__main__":
    main()
