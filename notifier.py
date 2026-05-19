import os
import json
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.swmaestro.ai"
LOGIN_PAGE = f"{BASE_URL}/sw/member/user/forLogin.do?menuNo=200025"
LOGIN_POST = f"{BASE_URL}/sw/member/user/toLogin.do"
LIST_URL = f"{BASE_URL}/sw/mypage/mentoLec/list.do?menuNo=200046&regDateOrder=desc"
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

    if "forLogin" in resp.url or "toLogin" in resp.url:
        return False

    # 마이페이지 메인을 먼저 방문해야 하위 페이지 접근 가능
    session.get(f"{BASE_URL}/sw/mypage/myMain/main.do?menuNo=200026")
    return True


def fetch_items(session: requests.Session) -> list[dict]:
    r = session.get(LIST_URL)
    soup = BeautifulSoup(r.text, "html.parser")

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
    for tr in target_table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue  # th만 있는 헤더 행 건너뜀

        cells = [re.sub(r'\s+', ' ', td.get_text()).strip() for td in tds]
        if len(cells) < len(headers):
            continue

        # 첫 번째 셀이 4자리 이상 숫자가 아니면 데이터 행이 아님
        if not re.search(r'\d{4,}', cells[0]):
            continue

        row = dict(zip(headers, cells))

        # 제목: <a> 태그 텍스트만 사용 (모바일용 숨겨진 텍스트 제외)
        try:
            title_idx = headers.index("제목")
            a_tag = tds[title_idx].find("a")
            if a_tag:
                row["제목"] = re.sub(r'\s+', ' ', a_tag.get_text()).strip()
        except ValueError:
            pass

        # 상세 링크 및 고유 ID (qustnrSn)
        link = tr.find("a", href=True)
        if link:
            row["_url"] = BASE_URL + link["href"]
            sn_match = re.search(r'qustnrSn=(\d+)', link["href"])
            row["_id"] = sn_match.group(1) if sn_match else None
        else:
            row["_url"] = LIST_URL
            row["_id"] = None

        items.append(row)

    return items


def send_slack(webhook_url: str, new_items: list[dict]) -> None:
    lines = [f"*새로운 멘토링/특강 {len(new_items)}개 등록됨!*"]
    for item in new_items:
        lines.append(
            f"• *<{item['_url']}|{item.get('제목', '')}>*\n"
            f"  🗓️ 등록일: {item.get('등록일', '')}\n"
            f"  📅 진행: {item.get('진행날짜', '')}\n"
            f"  ⏰ 접수: {item.get('접수기간', '')}\n"
            f"  👥 모집인원: {item.get('모집인원', '')}\n"
            f"  📌 상태: {item.get('상태', '')}\n"
            f"  ✏️ 작성자: {item.get('작성자', '')}"
        )
    requests.post(webhook_url, json={"text": "\n".join(lines)}, timeout=10)


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


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
        requests.post(webhook_url, json={"text": "[오류] 멘토링 목록 파싱 실패 — 로그를 확인하세요."}, timeout=10)
        return

    state = load_state()

    # seen_ids 없으면 첫 실행 or 구버전 마이그레이션 → 현재 항목 저장 후 종료
    if "seen_ids" not in state:
        all_ids = [i["_id"] for i in items if i.get("_id")]
        save_state({"seen_ids": all_ids})
        print("초기화 완료 — 다음 실행부터 새 글 감지 시작")
        return

    seen_ids = set(state["seen_ids"])
    new_items = [i for i in items if i.get("_id") and i["_id"] not in seen_ids]

    if new_items:
        send_slack(webhook_url, new_items)
        print(f"Notified: {len(new_items)} new item(s)")
    else:
        requests.post(webhook_url, json={"text": "새로운 멘토링/특강이 없습니다."}, timeout=10)
        print("No new items")

    # seen_ids 업데이트
    updated_ids = list(seen_ids | {i["_id"] for i in items if i.get("_id")})
    save_state({"seen_ids": updated_ids})


if __name__ == "__main__":
    main()
