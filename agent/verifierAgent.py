"""Second opinion on a research record: an agent that tries to refute each claim from the docs.

The verifier is given the claims but none of the first agent's evidence or reasoning, so it
has to find its own pages. Agreement from an agent that was shown the first agent's quotes
would mostly measure how persuasive those quotes read, not whether the claim is true.
"""

from agentLoop import runAgent
from appSchema import SCORED_FIELDS
from pipelineConfig import RUBRIC_PATH

VERDICT_AGREE = "agree"
VERDICT_DISAGREE = "disagree"
VERDICT_CANNOT_VERIFY = "cannotVerify"
VERDICTS = (VERDICT_AGREE, VERDICT_DISAGREE, VERDICT_CANNOT_VERIFY)

SYSTEM_PROMPT_INTRO = """You are a skeptical reviewer. Another researcher made claims about \
a software product's API. Your job is to check each claim against the vendor's own \
documentation and find the ones that are wrong.

Use the search and fetch tools to open the vendor's docs yourself: the authentication page, \
how a developer gets credentials (sign-up, plans, approval or sales contact), and whether the \
vendor publishes an MCP server. Do not rely on memory. Assume the claims may be wrong; \
researchers often call an API self-serve when it needs approval or a paid plan, miss an auth \
method, or miss an official MCP server.

For each field give a verdict: agree (the docs you opened support the claim), disagree (the \
docs you opened contradict it; give the value the rubric requires instead), or cannotVerify \
(you could not open docs that settle it). Only disagree when a page you opened shows the \
claim is wrong, and quote that page word for word.

When you have read enough, stop calling tools and summarise. You will then be asked for the \
verdicts. The rubric below defines every field and its allowed values.

"""
VERDICT_REQUEST = (
    "Now give your verdict on every field as JSON. Do not call tools. "
    "Quotes must be copied word for word from a page shown above."
)
VERDICT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdicts"],
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "verdict", "correctedValue", "reason", "url", "quote"],
                "properties": {
                    "field": {"type": "string", "enum": list(SCORED_FIELDS)},
                    "verdict": {"type": "string", "enum": list(VERDICTS)},
                    "correctedValue": {"type": "string"},
                    "reason": {"type": "string"},
                    "url": {"type": "string"},
                    "quote": {"type": "string"},
                },
            },
        }
    },
}


def verifyRecord(app, record, llmClient, toolbox):
    """Return {verdicts, toolCalls, usage, hitTurnLimit, model}."""
    outcome = runAgent(
        llmClient,
        toolbox,
        SYSTEM_PROMPT_INTRO + RUBRIC_PATH.read_text(encoding="utf-8"),
        buildTask(app, record),
        VERDICT_REQUEST,
        VERDICT_JSON_SCHEMA,
    )
    verdicts = outcome.pop("answer")["verdicts"]
    return {"verdicts": verdicts, **outcome}


def buildTask(app, record):
    claims = "\n".join(f"- {fieldName}: {record[fieldName]}" for fieldName in SCORED_FIELDS)
    return (
        f"Product: {app['name']}\n"
        f"Starting hint (website or docs): {app['hint']}\n\n"
        f"Claims to check:\n{claims}"
    )
