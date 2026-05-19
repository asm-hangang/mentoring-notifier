# mentoring-notifier

SW마에스트로 자유 멘토링 / 멘토 특강 새 글 알림 봇.  
30분마다 목록을 확인해 새 항목이 올라오면 Slack으로 알림을 보냅니다.

## 알림 예시

```
*새로운 멘토링/특강 1개 등록됨!*
• [자유 멘토링] 건전한소환사명팀 기획심의 준비
  🗓️ 등록일: 2026-05-20
  📅 진행: 2026-05-20(수) 10:00 ~ 11:00
  ⏰ 접수: 2026-05-20 00:00 ~ 2026-05-20 10:00
  👥 모집인원: 0 /3
  📌 상태: [접수중]
  ✏️ 작성자: 이주진
```

새 항목이 없으면 Slack 메시지를 보내지 않습니다.

## 설정

GitHub 레포 → **Settings → Secrets and variables → Actions** 에 아래 3개를 등록합니다.

| Secret 이름 | 설명 |
|---|---|
| `SW_USERNAME` | SW마에스트로 로그인 아이디 |
| `SW_PASSWORD` | SW마에스트로 비밀번호 |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

## 동작 방식

1. [cron-job.org](https://cron-job.org)이 30분마다 GitHub Actions `workflow_dispatch` 트리거
2. SW마에스트로에 로그인 (2단계 폼 제출 처리)
3. [멘토링/특강 목록](https://www.swmaestro.ai/sw/mypage/mentoLec/list.do?menuNo=200046) 파싱
4. 새 항목이 한 페이지(10개)를 전부 채우면 다음 페이지도 순차적으로 확인
5. 새 항목이 있으면 Slack 알림 발송
6. `last_seen.json` 업데이트 후 자동 커밋

## 프로젝트 구조

```
config.py   — URL 등 상수
auth.py     — SW마에스트로 로그인
scraper.py  — 멘토링 목록 스크래핑
slack.py    — Slack 알림 발송
state.py    — last_seen.json 읽기/쓰기
main.py     — 진입점
```

## 수동 실행

GitHub 레포 → **Actions → Mentoring Notifier → Run workflow**
