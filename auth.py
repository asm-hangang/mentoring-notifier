import requests
from bs4 import BeautifulSoup

from config import BASE_URL, LOGIN_PAGE, LOGIN_POST


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
