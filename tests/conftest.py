import sys
import types
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _DummyResponse:
    def raise_for_status(self):
        raise NotImplementedError("HTTP requests are not supported in tests.")

    def json(self):
        raise NotImplementedError("HTTP requests are not supported in tests.")


class _DummySession:
    def get(self, *args, **kwargs):
        return _DummyResponse()

    def post(self, *args, **kwargs):
        return _DummyResponse()


if "requests" not in sys.modules:
    requests_stub = types.SimpleNamespace(Session=_DummySession)
    sys.modules["requests"] = requests_stub
