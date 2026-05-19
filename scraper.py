import re

import requests
from bs4 import BeautifulSoup

from config import BASE_URL, LIST_URL


def fetch_items(session: requests.Session, page_index: int = 1) -> list[dict]:
    r = session.get(LIST_URL + f"&pageIndex={page_index}")
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
            continue

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
