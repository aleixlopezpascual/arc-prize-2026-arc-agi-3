from src.utils.retained_functions import (
    function_signature,
    prepare_functions,
    restore_functions,
)


def test_prepare_valid_functions():
    code = """
import math

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)
"""
    kept, rejected = prepare_functions([code], available=["math"])
    assert "distance" in kept
    assert len(rejected) == 0
    assert function_signature(code) == "distance(x1, y1, x2, y2)"


def test_reject_dangerous_or_decorated_functions():
    # Mutates global variable
    code_global = """
def mutate():
    global counter
    counter += 1
"""
    kept, rejected = prepare_functions([code_global], available=[])
    assert "mutate" not in kept
    assert len(rejected) == 1

    # Uses decorator
    code_decorated = """
@some_dec
def my_func():
    return 42
"""
    kept2, rejected2 = prepare_functions([code_decorated], available=[])
    assert "my_func" not in kept2
    assert len(rejected2) == 1


def test_restore_functions_in_clean_namespace():
    code = """
def add_ten(x):
    return x + 10
"""
    ns = {}
    survivors, rejected = restore_functions([code], namespace=ns, available=[])
    assert len(survivors) == 1
    assert len(rejected) == 0
    assert "add_ten" in ns
    assert ns["add_ten"](5) == 15
