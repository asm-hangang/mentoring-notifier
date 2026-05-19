import requests


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


def send_error(webhook_url: str, message: str) -> None:
    requests.post(webhook_url, json={"text": f"[오류] {message}"}, timeout=10)
