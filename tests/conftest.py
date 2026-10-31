import threading

import pytest

from app.server import make_server


@pytest.fixture(scope="session")
def base_url():
    """테스트 시작 시 서버를 빈 포트(0)로 띄우고, 끝나면 종료한다."""
    server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
