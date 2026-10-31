# notification-api-test

![API Test](https://github.com/wendyscode/notification-api-test/actions/workflows/test.yml/badge.svg)

문자 발송과 요금 계산을 하는 **연습용 가상 API**를 만들고, pytest로 API 테스트를 자동화한 뒤 GitHub Actions에서 자동 실행되게 한 개인 프로젝트입니다.

> 실제 서비스 API가 아닙니다. 단가와 규칙은 테스트 설계를 연습하기 위한 예시값입니다.

## 왜 만들었나

ISTQB CTFL에서 배운 테스트 설계 기법(경계값 분석, 동등 분할)을 실제 API 테스트 코드로 옮겨 보고, 코드를 올릴 때마다 테스트가 자동으로 돌아가는 CI 흐름을 직접 경험해 보려고 만들었습니다.

## 구성

```
app/server.py              연습용 API 서버 (파이썬 기본 라이브러리만 사용)
tests/conftest.py          테스트 시작 시 서버를 띄우고 끝나면 종료
tests/test_messages.py     문자 발송 API 테스트
tests/test_billing.py      요금 계산 API 테스트
.github/workflows/test.yml push할 때마다 Ubuntu·Windows에서 테스트 자동 실행
```

## API 규칙 (예시값)

| API | 규칙 |
|---|---|
| `POST /messages` | 본문을 EUC-KR 바이트로 계산 (한글 2B, 영문 1B). 1~90B는 SMS, 91~2000B는 LMS, 0B·2001B 이상·이모지는 400 오류. 수신번호는 01로 시작하는 10~11자리 |
| `POST /billing/estimate` | SMS 10원, LMS 30원. 합계 10,000건 초과분은 10% 할인. 음수·문자열·소수·불리언 건수는 400 오류 |
| `GET /health` | 상태 확인 |

## 테스트 케이스 설계 (31개)

| 대상 | 기법 | 케이스 | 기대 결과 |
|---|---|---|---|
| 본문 길이 | 경계값 | 0B / 1B / 90B / 91B / 2000B / 2001B | 오류 / SMS / SMS / LMS / LMS / 오류 |
| 한글 바이트 | 경계값 | 한글 45자(90B) / 46자(92B) | SMS / LMS |
| 한글+영문 | 경계값 | 한글 44자 + 영문 2자 = 90B | SMS |
| 특수 문자 | 오류 추정 | 이모지 포함 | 400 UNSUPPORTED_CHARACTER |
| 수신번호 | 동등 분할 | 정상(하이픈/숫자만/10자리), 자릿수 부족, 01 외 시작, 문자 포함, 빈 값 | 201 / 400 INVALID_PHONE |
| 할인 | 경계값 | 9,999건 / 10,000건 / 10,001건 / 11,000건 | 할인 0 / 0 / 1원 / 1,000원 |
| 건수 입력 | 동등 분할 | 0건, 정상, 음수, 문자열, 소수, 불리언 | 200 / 200 / 400 INVALID_COUNT |
| 요청 형식 | 오류 추정 | 깨진 JSON, 없는 경로 | 400 / 404 |

## 실행 방법

```bash
pip install -r requirements.txt
python -m pytest
```

서버만 따로 띄워서 확인하려면 `python -m app.server` 후 http://127.0.0.1:8000/health 접속.

## 배운 점

- **경계는 한 칸 안쪽과 바깥쪽을 같이 본다.** 90B와 91B를 같이 테스트해야 SMS/LMS 판정이 정확한지 알 수 있습니다.
- **한글은 바이트가 다르다.** 글자 수로만 테스트하면 한글 46자(92B)가 SMS로 잘못 처리되는 문제를 놓칠 수 있습니다.
- **입력 타입도 분할 대상이다.** 파이썬에서는 `True`가 숫자 1로 취급되기 때문에, 불리언을 건수로 보내는 케이스를 따로 넣었습니다.
- **CI는 "내 PC에서는 됐는데"를 없애 준다.** Ubuntu와 Windows 두 환경에서 같은 테스트가 자동으로 돌아갑니다.
