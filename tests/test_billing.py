"""요금 계산 API 테스트.

단가(예시값): SMS 10원, LMS 30원 / 합계 10,000건 초과분 10% 할인
- 경계값 분석: 10,000건(할인 없음) / 10,001건(할인 시작)
- 동등 분할: 0건 / 정상 건수 / 음수 / 숫자가 아닌 값
"""

import pytest
import requests


def estimate(base_url, **counts):
    return requests.post(f"{base_url}/billing/estimate", json=counts, timeout=5)


def test_zero_count(base_url):
    res = estimate(base_url, sms_count=0, lms_count=0)
    assert res.status_code == 200
    assert res.json() == {"total_count": 0, "base": 0, "discount": 0, "amount": 0}


def test_basic_amount(base_url):
    # SMS 100건 x 10원 + LMS 10건 x 30원 = 1,300원
    res = estimate(base_url, sms_count=100, lms_count=10)
    assert res.json()["amount"] == 1300


# 경계값: 할인 기준 10,000건
@pytest.mark.parametrize(
    "sms_count, expected_discount",
    [
        (9_999, 0),    # 기준 미만
        (10_000, 0),   # 기준과 같음: 할인 없음
        (10_001, 1),   # 1건 초과: 10원 x 10% = 1원
        (11_000, 1000),  # 1,000건 초과: 10,000원 x 10% = 1,000원
    ],
)
def test_discount_boundary(base_url, sms_count, expected_discount):
    res = estimate(base_url, sms_count=sms_count)
    body = res.json()
    assert res.status_code == 200
    assert body["discount"] == expected_discount
    assert body["amount"] == body["base"] - body["discount"]


@pytest.mark.parametrize(
    "counts",
    [
        {"sms_count": -1},
        {"lms_count": -5},
        {"sms_count": "100"},
        {"sms_count": 1.5},
        {"sms_count": True},
    ],
    ids=["음수SMS", "음수LMS", "문자열", "소수", "불리언"],
)
def test_invalid_count_returns_400(base_url, counts):
    res = estimate(base_url, **counts)
    assert res.status_code == 400
    assert res.json()["error"] == "INVALID_COUNT"
