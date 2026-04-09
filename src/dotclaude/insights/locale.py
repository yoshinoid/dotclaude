"""Detect the user's preferred locale for insight output.

Priority: LC_ALL -> LC_MESSAGES -> LANG -> locale.getdefaultlocale() -> default "en"
"""

from __future__ import annotations

import locale
import os


def detect_locale() -> str:
    """Detect the user's preferred locale.

    Returns "ko" for Korean, "en" for everything else.
    """
    # LC_ALL overrides all other locale settings when explicitly set
    lc_all = os.environ.get("LC_ALL", "")
    if lc_all:
        return "ko" if lc_all.lower().startswith("ko") else "en"

    for env_var in ("LC_MESSAGES", "LANG"):
        val = os.environ.get(env_var, "")
        if val.lower().startswith("ko"):
            return "ko"

    # Fallback to system locale
    try:
        system_locale = locale.getdefaultlocale()[0] or ""
        if system_locale.lower().startswith("ko"):
            return "ko"
    except (ValueError, AttributeError):
        pass

    return "en"
