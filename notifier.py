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

    resp = session.post(LOGIN_POST, data={
        "loginFlag": "",
        "menuNo": "200025",
        "csrfToken": csrf_input["value"],
        "username": username,
        "password": password,
    })

    # toLogin.do가 자동 제출 폼을 반환하면 /sw/login.do로 한 번 더 POST
    if "toLogin" in resp.url:
        soup2 = BeautifulSoup(resp.text, "html.parser")
        form2 = soup2.find("form")
        if not form2:
            return False
        action2 = BASE_URL + form2["action"]
        form_data = {i["name"]: i.get("value", "") for i in form2.find_all("input", {"type": "hidden"})}
        resp = session.post(action2, data=form_data)
        print(f"[DEBUG] Step2 POST final URL: {resp.url}, status: {resp.status_code}")

    if "forLogin" in resp.url or "toLogin" in resp.url:
        return False

    # 마이페이지 메인을 먼저 방문해야 하위 페이지 접근 가능
    session.get(f"{BASE_URL}/sw/mypage/myMain/main.do?menuNo=200026")
    return True


def fetch_items(session: requests.Session) -> list[dict]:
    r = session.get(LIST_URL)
    print(f"[DEBUG] fetch URL: {r.url}, status: {r.status_code}, len: {len(r.text)}")
    print(f"[DEBUG] HTML 앞부분: {r.text[:500]}")
    soup = BeautifulSoup(r.text, "html.parser")

    # 제목 컬럼이 있는 테이블을 찾음
    target_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "제목" in headers and "NO." in headers:
            target_table = table
            break

    if not target_table:
        all_headers = [
            [th.get_text(strip=True) for th in t.find_all("th")]
            for t in soup.find_all("table")
        ]
        print(f"[DEBUG] 테이블 헤더 목록: {all_headers}")
        return []

    headers = [th.get_text(strip=True) for th in target_table.find_all("th")]
    print(f"[DEBUG] 파싱된 헤더: {headers}")
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
        link = tr.find("a", href=True)
        row["_url"] = BASE_URL + link["href"] if link else LIST_URL
        items.append(row)

    return items


def send_slack(webhook_url: str, new_items: list[dict]) -> None:
    lines = [f"*새로운 멘토링/특강 {len(new_items)}개 등록됨!*"]
    for item in new_items:
        lines.append(
            f"• [{item.get('NO.', '')}] *<{item['_url']}|{item.get('제목', '')}>*\n"
            f"  📅 진행: {item.get('진행날짜', '')}\n"
            f"  ⏰ 접수: {item.get('접수기간', '')}\n"
            f"  👥 모집인원: {item.get('모집인원', '')}  |  {item.get('상태', '')}  |  작성자: {item.get('작성자', '')}"
        )
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
    print(f"[DEBUG] 파싱된 항목 수: {len(items)}")
    if not items:
        requests.post(webhook_url, json={"text": "[오류] 멘토링 목록 파싱 실패 — 로그를 확인하세요."}, timeout=10)
        return

    state = load_state()
    last_no = state["last_no"]

    new_items = [i for i in items if i["_no"] > last_no]

    if new_items:
        send_slack(webhook_url, new_items)
        print(f"Notified: {len(new_items)} new item(s)")
    else:
        requests.post(webhook_url, json={"text": "새로운 멘토링/특강이 없습니다."}, timeout=10)
        print("No new items")

    max_no = max(i["_no"] for i in items)
    if max_no > last_no:
        save_state({"last_no": max_no})
        print(f"State updated: last_no={max_no}")


if __name__ == "__main__":
    main()
