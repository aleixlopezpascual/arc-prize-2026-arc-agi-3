from src.perception.manual_injector import install


def test_manual_injector_empty():
    assert install({}) is None


def test_manual_injector_disabled():
    assert install({"game1": "manual"}, enabled=False) is None
