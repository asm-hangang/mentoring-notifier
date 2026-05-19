# mentoring-notifier

SW마에스트로 자유 멘토링 / 멘토 특강 새 글 알림 봇.  
30분마다 목록을 확인해 새 항목이 올라오면 Slack으로 알림을 보냅니다.

## 알림 예시

```
*새로운 멘토링/특강 1개 등록됨!*
• [2321] *[자유 멘토링] 제목*
  📅 진행: 2026-06-01(월) 13:00 ~ 15:00
  ⏰ 접수: 2026-05-18 01:00 ~ 2026-06-01 13:00
  👥 모집인원: 0 /3  |  [접수중]  |  작성자: 홍길동
```

새 항목이 없으면 `새로운 멘토링/특강이 없습니다.` 메시지를 보냅니다.

## 설정

GitHub 레포 → **Settings → Secrets and variables → Actions** 에 아래 3개를 등록합니다.

| Secret 이름 | 설명 |
|---|---|
| `SW_USERNAME` | SW마에스트로 로그인 아이디 |
| `SW_PASSWORD` | SW마에스트로 비밀번호 |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

## 동작 방식

1. GitHub Actions cron이 30분마다 `notifier.py` 실행
2. SW마에스트로에 로그인 (2단계 폼 제출 처리)
3. [멘토링/특강 목록](https://www.swmaestro.ai/sw/mypage/mentoLec/list.do?menuNo=200046) 파싱
4. `last_seen.json`에 저장된 마지막 NO.보다 큰 항목이 있으면 Slack 알림 발송
5. `last_seen.json` 업데이트 후 자동 커밋

## 수동 실행

GitHub 레포 → **Actions → Mentoring Notifier → Run workflow**
