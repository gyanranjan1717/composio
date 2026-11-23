"""Paths, model choices and limits shared by every pipeline stage."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPS_PATH = PROJECT_ROOT / "data" / "apps.json"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
PAGE_CACHE_DIR = PROJECT_ROOT / "data" / "cache"
GOLD_SAMPLE_PATH = PROJECT_ROOT / "data" / "goldSample.json"
SCORES_DIR = PROJECT_ROOT / "data" / "scores"
RUBRIC_PATH = Path(__file__).resolve().parent / "labellingRubric.md"

# Tried in order. On 2026-11-23 the free tier answered 503/504 on every Flash model tested
# and only flash-lite responded, so the list ends on the model that was actually available.
MODEL_PREFERENCE = (
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)
REQUEST_TIMEOUT_MILLISECONDS = 90000

COMPOSIO_USER_ID = "researchAgent"
# Composio's own composio_search toolkit is retired (HTTP 410 on execute), so search runs on
# its Tavily toolkit with the user's Tavily key. The version is pinned because Composio
# refuses direct execution without one.
SEARCH_TOOLKIT = "tavily"
SEARCH_TOOLKIT_VERSION = "20261103_00"
SEARCH_TOOL_SLUG = "TAVILY_SEARCH"

MAX_AGENT_TURNS = 12
# Docs pages can run to hundreds of thousands of characters; the agent only needs the part
# that states auth and access, and an unbounded page would crowd out everything else.
MAX_TOOL_RESULT_CHARS = 20000
# Free-tier Gemini keys have low per-minute request limits.
MAX_PARALLEL_APPS = 8
RATE_LIMIT_RETRY_DELAYS_SECONDS = (20, 45, 90, 150)
