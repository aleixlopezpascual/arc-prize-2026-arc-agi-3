import pytest
from src.perception.phase_a_setup import _GATEWAY_HOST_ALLOWLIST, wait_for_gateway


def test_allowlist():
    assert "gateway" in _GATEWAY_HOST_ALLOWLIST
    assert "127.0.0.1" in _GATEWAY_HOST_ALLOWLIST


def test_wait_for_gateway_invalid_host():
    with pytest.raises(RuntimeError, match="Unexpected gateway host"):
        wait_for_gateway("http://evil-external-host.com:8001/")
