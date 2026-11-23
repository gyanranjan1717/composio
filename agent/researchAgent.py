"""Researches one app: reads the vendor's docs through tools, then fills the fixed schema."""

from agentLoop import runAgent
from appSchema import RECORD_JSON_SCHEMA, validateRecord
from pipelineConfig import RUBRIC_PATH

SYSTEM_PROMPT_INTRO = """You research one software product for a team that builds API \
integrations ("toolkits") that AI agents call. For the product you are given, find out from \
the vendor's own documentation how its public API is authenticated, how a developer gets \
credentials, what the API covers, and whether an MCP server exists.

Use the search and fetch tools to open the vendor's developer docs, authentication page and \
pricing or plans page, and check for an MCP server. Open the pages; do not answer from memory, \
because auth schemes and access rules change and your answer will be checked against the live \
page. Every quote you cite must be copied exactly from a page you opened in this conversation.

If the docs are thin, missing or blocked, say so through the fields (for example \
mainBlocker = thinOrMissingDocs) instead of guessing. A truthful "gated" or "no public API" \
with evidence is a correct result.

When you have read enough, stop calling tools and summarise what you found and where. You \
will then be asked for the final record. The rubric below defines every field.

"""
RECORD_REQUEST = (
    "Now give the final record as JSON, following the rubric exactly. Do not call tools. "
    "Every evidence quote must be copied word for word from a page shown above."
)
REVISION_HEADING = (
    "\n\nAn earlier answer for this product was checked and these problems were found. "
    "Research the product again from the docs and fix them. Where a problem says a quote was "
    "not on its page, open the page with fetchPage and copy a real sentence from it; never "
    "quote a search snippet or a page you could not open.\n"
)


def researchApp(app, llmClient, toolbox, reviewerNotes=""):
    """Return {record, validationProblems, toolCalls, usage, hitTurnLimit, model}."""
    outcome = runAgent(
        llmClient,
        toolbox,
        SYSTEM_PROMPT_INTRO + RUBRIC_PATH.read_text(encoding="utf-8"),
        buildTask(app, reviewerNotes),
        RECORD_REQUEST,
        RECORD_JSON_SCHEMA,
    )
    record = outcome.pop("answer")
    return {"record": record, "validationProblems": validateRecord(record), **outcome}


def buildTask(app, reviewerNotes):
    task = (
        f"Product: {app['name']}\n"
        f"Category in our list: {app['category']}\n"
        f"Starting hint (website or docs): {app['hint']}"
    )
    if reviewerNotes:
        task += REVISION_HEADING + reviewerNotes
    return task
