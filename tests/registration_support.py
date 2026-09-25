"""시험용 로컬 등록 도우미(카드 #71). 사용자의 실제 등록 파일과 machine-id를 건드리지 않는다.

관측 기록의 다른 성질(날짜·판·권한·재읽기)을 보는 시험은 "이 기기에 등록돼 있다"를 가정한다 — 등록 자체는
tests/test_registration.py가 따로 본다. 가정을 숨기지 않으려고 쓰는 곳마다 이 함수를 부른다.
"""
import os
from pathlib import Path
import tempfile
from unittest import mock


def assume_registered(test) -> None:
    """이 시험 동안 등록 검사가 통과한다고 둔다(app.registration.problem → None)."""
    patcher = mock.patch("app.registration.problem", return_value=None)
    patcher.start()
    test.addCleanup(patcher.stop)


def isolate(test) -> Path:
    """이 시험 동안 등록 파일과 machine-id를 임시 파일로 바꾼다. 돌려주는 폴더에 둘이 있다."""
    tmp = tempfile.TemporaryDirectory(prefix="dml-registration-")
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name)
    (root / "machine-id").write_text("0123456789abcdef0123456789abcdef\n", encoding="ascii")
    patcher = mock.patch.dict(os.environ, {"DML_REGISTRATION_FILE": str(root / "registrations.json"),
                                           "DML_MACHINE_ID_FILE": str(root / "machine-id")})
    patcher.start()
    test.addCleanup(patcher.stop)
    return root
