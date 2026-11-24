"""Compatibility alias: text normalisation lives in _shared/scholarly.textnorm.

Aliased rather than re-exported for the same reason as sources.py — see that
module's docstring.
"""
import os
import sys

_SHARED = next((str(_p / "_shared") for _p in __import__("pathlib").Path(__file__).resolve().parents if _p.name == "skills" and (_p / "_shared").is_dir()), __import__("os").path.expanduser("~/.claude/skills/_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly import textnorm as _textnorm  # noqa: E402

sys.modules[__name__] = _textnorm
