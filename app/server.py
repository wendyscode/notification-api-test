"""연습용 가상 알림(SMS) API 서버.

실제 NHN Cloud API가 아니라, 테스트 자동화를 연습하려고 만든 작은 서버입니다.
파이썬 기본 라이브러리만 사용합니다.

엔드포인트
- GET  /health             : 서버 상태 확인
- POST /messages           : 문자 발송 요청 (본문 길이에 따라 SMS/LMS 결정)
- POST /billing/estimate   : 발송 건수로 예상 요금 계산

규칙 (연습용 예시값)
- 본문은 EUC-KR 기준 바이트로 계산 (한글 2바이트, 영문·숫자 1바이트)
- 1~90바이트: SMS / 91~2000바이트: LMS / 0바이트 또는 2000바이트 초과: 오류
- 수신번호: 01로 시작하는 숫자 10~11자리 (하이픈 허용)
- 단가: SMS 10원, LMS 30원 (예시값)
- 월 합계 10,000건 초과분은 10% 할인
"""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SMS_MAX_BYTES = 90
LMS_MAX_BYTES = 2000
PRICE = {"SMS": 10, "LMS": 30}
DISCOUNT_THRESHOLD = 10_000
DISCOUNT_RATE = 0.10
PHONE_PATTERN = re.compile(r"^01\d{8,9}$")


def message_bytes(body: str) -> int:
    """EUC-KR 기준 바이트 수. EUC-KR로 표현할 수 없는 문자(이모지 등)는 오류로 본다."""
    return len(body.encode("euc-kr"))


def classify(body: str) -> str:
    size = message_bytes(body)
    if size == 0:
        raise ValueError("EMPTY_BODY")
    if size <= SMS_MAX_BYTES:
        return "SMS"
    if size <= LMS_MAX_BYTES:
        return "LMS"
    raise ValueError("BODY_TOO_LONG")


def normalize_phone(phone: str) -> str:
    digits = phone.replace("-", "")
    if not PHONE_PATTERN.match(digits):
        raise ValueError("INVALID_PHONE")
    return digits


def estimate(sms_count: int, lms_count: int) -> dict:
    for value in (sms_count, lms_count):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("INVALID_COUNT")
    total_count = sms_count + lms_count
    base = sms_count * PRICE["SMS"] + lms_count * PRICE["LMS"]
    discount = 0
    if total_count > DISCOUNT_THRESHOLD:
        # 초과분에 대해서만 할인 (평균 단가 기준)
        average = base / total_count
        discount = round((total_count - DISCOUNT_THRESHOLD) * average * DISCOUNT_RATE)
    return {"total_count": total_count, "base": base, "discount": discount, "amount": base - discount}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 테스트 출력이 지저분해지지 않게 로그 끔
        pass

    def _send(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return None

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        return self._send(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        payload = self._read_json()
        if payload is None:
            return self._send(400, {"error": "INVALID_JSON"})

        if self.path == "/messages":
            try:
                to = normalize_phone(str(payload.get("to", "")))
                body = payload.get("body", "")
                if not isinstance(body, str):
                    raise ValueError("EMPTY_BODY")
                message_type = classify(body)
            except UnicodeEncodeError:
                return self._send(400, {"error": "UNSUPPORTED_CHARACTER"})
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            return self._send(201, {"to": to, "type": message_type, "bytes": message_bytes(body)})

        if self.path == "/billing/estimate":
            try:
                result = estimate(payload.get("sms_count", 0), payload.get("lms_count", 0))
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            return self._send(200, result)

        return self._send(404, {"error": "NOT_FOUND"})


def make_server(port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    server = make_server()
    print("http://127.0.0.1:8000 에서 실행 중 (종료: Ctrl+C)")
    server.serve_forever()
