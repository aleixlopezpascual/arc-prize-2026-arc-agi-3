from __future__ import annotations

import ast
import dis
import types
from collections.abc import Sequence
from typing import Any


def _import_statements(nodes: Sequence[ast.AST]) -> dict[str, str]:
    statements = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                binding = alias.asname or alias.name.split(".")[0]
                statements[binding] = ast.unparse(ast.Import(names=[alias]))
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            for alias in node.names:
                if alias.name == "*":
                    raise ValueError("wildcard imports are not retained")
                statements[alias.asname or alias.name] = ast.unparse(
                    ast.ImportFrom(module=node.module, names=[alias], level=0)
                )
    return statements


def _source_parts(
    source: str, retain_imports: bool = True
) -> tuple[ast.FunctionDef, dict[str, str]]:
    tree = ast.parse(source, "<retained>", "exec")
    if not tree.body or not isinstance(tree.body[-1], ast.FunctionDef):
        raise ValueError("only top-level function definitions can be retained")
    imports = _import_statements(tree.body[:-1]) if retain_imports else {}
    return tree.body[-1], imports


def function_signature(source: str) -> str:
    node, _ = _source_parts(source, retain_imports=False)
    return f"{node.name}({ast.unparse(node.args)})"


def _function_record(source: str) -> tuple[str, str, set[str]]:
    node, imports = _source_parts(source, retain_imports=True)
    if node.decorator_list:
        raise ValueError("decorated functions are not retained")

    tree = ast.Module(body=[node], type_ignores=[])
    code = next(
        c
        for c in compile(tree, "<retained>", "exec").co_consts
        if isinstance(c, types.CodeType)
    )
    reads = set()
    pending = [code]

    while pending:
        curr = pending.pop()
        for instr in dis.get_instructions(curr):
            if instr.opname in ("LOAD_GLOBAL", "LOAD_NAME"):
                reads.add(instr.argval)
            elif instr.opname in ("STORE_GLOBAL", "DELETE_GLOBAL"):
                raise ValueError("functions that assign global variables are not retained")
        pending.extend(c for c in curr.co_consts if isinstance(c, types.CodeType))

    return node.name, source, reads - imports.keys()


def prepare_functions(
    sources: Sequence[str],
    available: Sequence[str] | set[str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    records: dict[str, tuple[str, set[str]]] = {}
    rejected: list[dict[str, Any]] = []

    for source in sources:
        name = "<unknown>"
        try:
            name, src, reads = _function_record(source)
            records[name] = (src, reads)
        except Exception as exc:  # noqa: BLE001
            rejected.append({"name": name, "reason": str(exc)})

    # Prune functions with missing dependencies
    avail_set = set(available)
    while True:
        dropped = []
        for name, (src, reads) in records.items():
            missing = reads - avail_set - records.keys()
            if missing:
                dropped.append(name)
                rejected.append({"name": name, "reason": f"missing dependencies: {missing}"})
        if not dropped:
            break
        for name in dropped:
            del records[name]

    return {name: val[0] for name, val in records.items()}, rejected


def restore_functions(
    sources: Sequence[str],
    namespace: dict[str, Any],
    available: Sequence[str] | set[str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    kept, rejected = prepare_functions(sources, available)
    failed = set()

    for name, source in kept.items():
        try:
            exec(compile(source, "<retained>", "exec"), namespace, namespace)  # noqa: S102
        except Exception as exc:  # noqa: BLE001
            failed.add(name)
            rejected.append({"name": name, "reason": f"exec failed: {exc}"})

    survivors = {name: src for name, src in kept.items() if name not in failed}
    return survivors, rejected
