"""manual_injector.py - Injects pre-exploration manuals into solver game sessions.

Appends ground-truth pre-exploration manuals into analyzer._system_prompt at
session start (maintaining 100% RadixAttention prefix caching within each game stream).
"""
from __future__ import annotations

import os
from typing import Any, Callable, Mapping

DEFAULT_HEADER = (
    "\n\nPre-exploration report (generated before this session by a scripted explorer that "
    "probed a separate instance of this exact game, same initial board):\n"
    "Use these verified facts as your starting world model instead of spending early turns "
    "re-discovering action semantics. They were measured on the level-0 initial board; later "
    "levels may change mechanics, so re-verify effects there before relying on them.\n"
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes"}


def install(
    manuals: Mapping[str, str],
    *,
    header: str = DEFAULT_HEADER,
    enabled: bool | None = None,
    log: Callable[[str], None] = print,
) -> Callable[[], None] | None:
    if enabled is None:
        enabled = _env_bool("ENABLE_MANUAL_INJECT", True)
    if not enabled:
        log("[v22-manual] disabled (ENABLE_MANUAL_INJECT=0)")
        return None
    manuals = {k: v for k, v in dict(manuals).items() if isinstance(v, str) and v}
    if not manuals:
        log("[v22-manual] no manuals; skipping install")
        return None

    try:
        from inference.framework.solver import _HarnessGameSession as target_cls
    except Exception as exc:
        log(f"[v22-manual] install failed (import): {exc}")
        return None

    if getattr(target_cls, "_v22_manual_injector_installed", False):
        log("[v22-manual] already installed")
        return None

    orig_play = target_cls.play

    def patched_play(self: Any) -> Any:
        try:
            gid = getattr(getattr(self, "game", None), "env_name", None)
            manual = manuals.get(gid)
            analyzer = getattr(self, "analyzer", None)
            if manual and analyzer is not None:
                base = getattr(analyzer, "_system_prompt", None)
                if isinstance(base, str) and not getattr(analyzer, "_v22_manual_injected", False):
                    analyzer._system_prompt = base + header + manual
                    analyzer._v22_manual_injected = True
                    log(f"[v22-manual] injected {gid} (+{len(header) + len(manual)} chars)")
        except Exception as exc:
            log(f"[v22-manual] inject failed: {type(exc).__name__}: {exc}")
        return orig_play(self)

    target_cls.play = patched_play
    target_cls._v22_manual_injector_installed = True
    log(f"[v22-manual] installed: {len(manuals)} manuals keyed by env_name")

    def revert() -> None:
        target_cls.play = orig_play
        target_cls._v22_manual_injector_installed = False

    return revert
