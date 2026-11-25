"""Sentinel analyst workspace API: a thin service over `sentinel_aml_agent/`, which it imports and never edits.

`sentinel_aml_agent` uses top-level packages (`utils`, `tools`, `rules`, `agents`), so its folder goes on `sys.path`
before anything from it is imported.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = REPO_ROOT / "sentinel_aml_agent"
UI_ROOT = REPO_ROOT / "sentinel_ui"

if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))
