"""Turns the outputs of the three checks into a plain list of problems per app.

The checks are: the deterministic evidence check, the Composio catalog cross-check and the
verifier agent. The problem list is what the re-research step hands back to the research
agent, and what the case study shows as "why this app was sent back".
"""

from evidenceChecker import PAGE_UNREADABLE, QUOTE_NOT_FOUND
from resultStore import loadPassResults
from verifierAgent import VERDICT_DISAGREE

EVIDENCE_SUFFIX = "Evidence"
CATALOG_SUFFIX = "Catalog"
VERIFIER_SUFFIX = "Verifier"
SOURCE_SCHEMA = "schema"
SOURCE_EVIDENCE = "evidenceCheck"
SOURCE_CATALOG = "composioCatalog"
SOURCE_VERIFIER = "verifierAgent"


def collectIssues(passName):
    """Return {appId: [{source, field, message}]} for every app with at least one problem."""
    issuesById = {}

    def add(appId, source, field, message):
        issuesById.setdefault(appId, []).append(
            {"source": source, "field": field, "message": message}
        )

    for result in loadPassResults(passName):
        for problem in result.get("validationProblems") or []:
            add(result["id"], SOURCE_SCHEMA, problem.split(":")[0], f"Schema problem: {problem}")
    for item in loadPassResults(passName + EVIDENCE_SUFFIX):
        for check in item["checks"]:
            addEvidenceIssue(add, item["id"], check)
    for item in loadPassResults(passName + CATALOG_SUFFIX):
        addCatalogIssues(add, item)
    for item in loadPassResults(passName + VERIFIER_SUFFIX):
        for verdict in item["verdicts"] or []:
            addVerifierIssue(add, item["id"], verdict)
    return issuesById


def addEvidenceIssue(add, appId, check):
    if check["status"] == QUOTE_NOT_FOUND:
        add(
            appId,
            SOURCE_EVIDENCE,
            check["field"],
            f"The quote cited for {check['field']} is not on the page {check['url']}.",
        )
    if check["status"] == PAGE_UNREADABLE:
        add(
            appId,
            SOURCE_EVIDENCE,
            check["field"],
            f"The page cited for {check['field']} could not be opened ({check['url']}). "
            "Cite a page that fetchPage can open.",
        )


def addCatalogIssues(add, item):
    if item["missing"] and item["status"] == "disagrees":
        add(
            item["id"],
            SOURCE_CATALOG,
            "authMethods",
            f"Composio's existing toolkit for this app authenticates with "
            f"{item['composioAuthMethods']}, but authMethods does not include {item['missing']}. "
            "Check the vendor's auth docs for those methods.",
        )
    if item["mcpContradiction"]:
        add(
            item["id"],
            SOURCE_CATALOG,
            "existingMcp",
            f"Composio's catalog has an MCP toolkit for this app ({item['mcpToolkitSlug']}), "
            "which suggests the vendor has an MCP server, but existingMcp says none. Check.",
        )


def addVerifierIssue(add, appId, verdict):
    if verdict["verdict"] != VERDICT_DISAGREE:
        return
    add(
        appId,
        SOURCE_VERIFIER,
        verdict["field"],
        f"A reviewer disagrees on {verdict['field']} and says it should be "
        f"'{verdict['correctedValue']}'. Reason: {verdict['reason']} (source: {verdict['url']})",
    )
