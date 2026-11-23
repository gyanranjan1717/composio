"""The two tools the agents get: web search (Composio's Tavily toolkit) and page reading."""

import os

from composio import Composio
from google.genai import types

from pageFetcher import fetchPage
from pipelineConfig import (
    COMPOSIO_USER_ID,
    MAX_TOOL_RESULT_CHARS,
    SEARCH_TOOL_SLUG,
    SEARCH_TOOLKIT,
    SEARCH_TOOLKIT_VERSION,
)

SEARCH_TOOL_NAME = "searchWeb"
FETCH_TOOL_NAME = "fetchPage"
MAX_SEARCH_RESULTS = 6
SEARCH_RESULT_FIELDS = ("title", "url", "content")
TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name=SEARCH_TOOL_NAME,
        description=(
            "Search the web. Returns titles, URLs and short snippets. Snippets are not "
            "evidence: open the page with fetchPage before quoting it."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query."}},
            "required": ["query"],
        },
    ),
    types.FunctionDeclaration(
        name=FETCH_TOOL_NAME,
        description=(
            "Open a public web page and return its readable text. Long pages are cut off; "
            "pass 'find' to get the part of the page around a word or phrase instead of "
            "the beginning."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full https URL of the page."},
                "find": {
                    "type": "string",
                    "description": "Optional word or phrase to centre the returned text on.",
                },
            },
            "required": ["url"],
        },
    ),
]


class ComposioToolbox:
    def __init__(self, composio):
        self.composio = composio
        self.handlers = {SEARCH_TOOL_NAME: self.searchWeb, FETCH_TOOL_NAME: readPage}

    def run(self, toolName, arguments):
        """Execute one tool call; return (payload for the model, whether it failed)."""
        try:
            payload = self.handlers[toolName](**arguments)
        # A bad argument or tool name from the model must come back to it as a failed call
        # it can correct, not end the whole app's research.
        except Exception as error:
            return {"error": f"Tool call failed: {error}"}, True
        return payload, "error" in payload

    def searchWeb(self, query):
        result = self.composio.tools.execute(
            SEARCH_TOOL_SLUG,
            {"query": query, "max_results": MAX_SEARCH_RESULTS},
            user_id=COMPOSIO_USER_ID,
        )
        if not result["successful"]:
            return {"error": str(result["error"])}
        return {"results": [pickFields(hit) for hit in findSearchHits(result["data"])]}


def buildToolbox():
    composio = Composio(
        api_key=os.environ["COMPOSIO_API_KEY"],
        toolkit_versions={SEARCH_TOOLKIT: SEARCH_TOOLKIT_VERSION},
    )
    return ComposioToolbox(composio)


def findSearchHits(data):
    """Composio wraps Tavily's response; the hit list sits under 'results' at one of two depths."""
    if "results" in data:
        return data["results"]
    return data["response_data"]["results"]


def pickFields(hit):
    return {field: hit[field] for field in SEARCH_RESULT_FIELDS}


def readPage(url, find=None):
    page = fetchPage(url)
    if page["error"] is not None:
        return {"error": f"Could not open {url}: {page['error']}"}
    text = page["text"]
    start = windowStart(text, find)
    return {
        "url": page["finalUrl"],
        "totalCharacters": len(text),
        "shownFromCharacter": start,
        "text": text[start : start + MAX_TOOL_RESULT_CHARS],
    }


def windowStart(text, find):
    if not find:
        return 0
    position = text.lower().find(find.lower())
    if position < 0:
        return 0
    return max(0, position - MAX_TOOL_RESULT_CHARS // 2)
