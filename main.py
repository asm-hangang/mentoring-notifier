import os

import requests

from auth import login
from scraper import fetch_items
from slack import send_error, send_slack
from state import load_state, save_state


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

    first_page = fetch_items(session, page_index=1)
    if not first_page:
        send_error(webhook_url, "멘토링 목록 파싱 실패 — 로그를 확인하세요.")
        return

    state = load_state()

    # seen_ids 없으면 첫 실행 → 현재 항목 저장 후 종료
    if "seen_ids" not in state:
        all_ids = [i["_id"] for i in first_page if i.get("_id")]
        save_state({"seen_ids": all_ids})
        print("초기화 완료 — 다음 실행부터 새 글 감지 시작")
        return

    seen_ids = set(state["seen_ids"])
    all_new_items = []
    all_fetched_ids = set()

    page = 1
    while True:
        items = fetch_items(session, page_index=page) if page > 1 else first_page
        if not items:
            break
        all_fetched_ids.update(i["_id"] for i in items if i.get("_id"))
        new_on_page = [i for i in items if i.get("_id") and i["_id"] not in seen_ids]
        all_new_items.extend(new_on_page)
        # 페이지 전체가 새 글이면 다음 페이지도 확인
        if len(new_on_page) == len(items):
            page += 1
        else:
            break

    if all_new_items:
        send_slack(webhook_url, all_new_items)
        print(f"Notified: {len(all_new_items)} new item(s)")
    else:
        print("No new items")

    updated_ids = list(seen_ids | all_fetched_ids)
    save_state({"seen_ids": updated_ids})


if __name__ == "__main__":
    main()
