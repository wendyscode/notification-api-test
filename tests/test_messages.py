"""문자 발송 API 테스트.

ISTQB 테스트 설계 기법
- 경계값 분석: 90/91바이트(SMS↔LMS), 2000/2001바이트(LMS↔오류), 0/1바이트
- 동등 분할: 정상 번호 / 짧은 번호 / 01로 시작하지 않는 번호 / 문자 포함 번호
"""

import pytest
import requests


def send(base_url, to="010-1234-5678", body="안녕하세요"):
    return requests.post(f"{base_url}/messages", json={"to": to, "body": body}, timeout=5)


def test_health(base_url):
    res = requests.get(f"{base_url}/health", timeout=5)
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# 경계값 분석: 본문 바이트 수에 따른 SMS / LMS / 오류
@pytest.mark.parametrize(
    "body, expected_status, expected_type",
    [
        ("", 400, None),            # 0바이트: 오류
        ("a", 201, "SMS"),          # 1바이트: SMS 최소
        ("a" * 90, 201, "SMS"),     # 90바이트: SMS 최대
        ("a" * 91, 201, "LMS"),     # 91바이트: LMS 최소
        ("a" * 2000, 201, "LMS"),   # 2000바이트: LMS 최대
        ("a" * 2001, 400, None),    # 2001바이트: 오류
    ],
    ids=["0B", "1B", "90B", "91B", "2000B", "2001B"],
)
def test_message_type_boundary(base_url, body, expected_status, expected_type):
    res = send(base_url, body=body)
    assert res.status_code == expected_status
    if expected_type:
        assert res.json()["type"] == expected_type


# 한글은 2바이트: 45자(90B)는 SMS, 46자(92B)는 LMS
@pytest.mark.parametrize("length, expected_type", [(45, "SMS"), (46, "LMS")])
def test_korean_counts_two_bytes(base_url, length, expected_type):
    res = send(base_url, body="가" * length)
    assert res.status_code == 201
    assert res.json() == {"to": "01012345678", "type": expected_type, "bytes": length * 2}


# 한글+영문 섞인 경우: 한글 44자(88B) + 영문 2자(2B) = 90B → SMS
def test_mixed_korean_english_at_boundary(base_url):
    res = send(base_url, body="가" * 44 + "ab")
    assert res.json()["bytes"] == 90
    assert res.json()["type"] == "SMS"


def test_emoji_is_rejected(base_url):
    res = send(base_url, body="생일 축하해요 🎂")
    assert res.status_code == 400
    assert res.json()["error"] == "UNSUPPORTED_CHARACTER"


# 동등 분할: 수신번호
@pytest.mark.parametrize(
    "to, expected_status",
    [
        ("010-1234-5678", 201),  # 정상 (하이픈 포함)
        ("01012345678", 201),    # 정상 (숫자만)
        ("0111234567", 201),     # 정상 10자리
        ("010-123-456", 400),    # 자릿수 부족
        ("02-123-4567", 400),    # 01로 시작하지 않음
        ("010-abcd-5678", 400),  # 문자 포함
        ("", 400),               # 빈 값
    ],
)
def test_phone_validation(base_url, to, expected_status):
    res = send(base_url, to=to)
    assert res.status_code == expected_status
    if expected_status == 400:
        assert res.json()["error"] == "INVALID_PHONE"


def test_invalid_json_returns_400(base_url):
    res = requests.post(f"{base_url}/messages", data="{not json", timeout=5)
    assert res.status_code == 400
    assert res.json()["error"] == "INVALID_JSON"


def test_unknown_path_returns_404(base_url):
    res = requests.get(f"{base_url}/unknown", timeout=5)
    assert res.status_code == 404
