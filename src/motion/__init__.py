"""React + Framer Motion views rendered as a Streamlit custom component.

Source lives in `frontend/`; `npm run build` there writes the compiled bundle to `src/motion/dist`,
which is committed so deployments need no Node toolchain.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_DIST = Path(__file__).parent / "dist"
_component = components.declare_component("askmydocs_motion", path=str(_DIST))


def motion_view(view: str, key: str, **data: Any) -> Any:
    """Render a motion view ("landing", "stats" or "flashcards"); returns the last event it sent, if any."""
    return _component(view=view, key=key, default=None, **data)
