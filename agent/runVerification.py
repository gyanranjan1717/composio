"""Runs the verification loops on one pass and re-researches the apps that failed a check.

    python agent/runVerification.py --fromPass pass1 --toPass pass2 --step verify
    python agent/runVerification.py --fromPass pass1 --toPass pass2 --step reresearch

--step verify      runs the verifier agent on every record of fromPass.
--step reresearch  collects the problems from all three checks, sends each flagged app back
                   to the research agent with its problem list, and copies unflagged apps
                   across unchanged, so toPass always holds all 100.
Run agent/evidenceChecker.py and agent/composioCatalogCheck.py on fromPass before
--step reresearch; they are deterministic and need no model.
"""

import argparse
import json

from dotenv import load_dotenv

from composioToolbox import buildToolbox
from geminiClient import buildLlmClient
from issueCollector import VERIFIER_SUFFIX, collectIssues
from passRunner import runPass
from pipelineConfig import PROJECT_ROOT
from researchAgent import researchApp
from resultStore import loadPassResults, resultPath, saveResult
from verifierAgent import verifyRecord

STEP_VERIFY = "verify"
STEP_RERESEARCH = "reresearch"
ISSUES_SUFFIX = "Issues"


def main():
    parser = argparse.ArgumentParser(description="Verify a pass and re-research flagged apps.")
    parser.add_argument("--fromPass", required=True)
    parser.add_argument("--toPass", required=True)
    parser.add_argument("--step", required=True, choices=(STEP_VERIFY, STEP_RERESEARCH))
    parser.add_argument(
        "--onlyIds", type=int, nargs="+", help="re-research only these apps; others carry over"
    )
    arguments = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    toolbox = buildToolbox()
    llmClient = buildLlmClient()
    results = loadPassResults(arguments.fromPass)
    if arguments.step == STEP_VERIFY:
        runVerifier(arguments.fromPass, results, llmClient, toolbox)
        return
    runReResearch(
        arguments.fromPass, arguments.toPass, results, llmClient, toolbox, arguments.onlyIds
    )


def runVerifier(fromPass, results, llmClient, toolbox):
    recordsById = {result["id"]: result["record"] for result in results}
    apps = [toApp(result) for result in results if result["record"] is not None]
    runPass(
        fromPass + VERIFIER_SUFFIX,
        apps,
        lambda app: verifyRecord(app, recordsById[app["id"]], llmClient, toolbox),
        lambda result: f"{countDisagreements(result)} disagreement(s), model {result['model']}",
        {"verdicts": None},
    )


def runReResearch(fromPass, toPass, results, llmClient, toolbox, onlyIds):
    issuesById = collectIssues(fromPass)
    flagged = []
    for result in results:
        issues = issuesById.get(result["id"], [])
        saveResult(fromPass + ISSUES_SUFFIX, {"id": result["id"], "name": result["name"], "issues": issues})
        inScope = onlyIds is None or result["id"] in onlyIds
        if inScope and (issues or result["record"] is None):
            flagged.append(toApp(result))
        elif not alreadyReResearched(toPass, result["id"]):
            saveResult(toPass, {**result, "carriedFrom": fromPass})
    notesById = {
        appId: "\n".join(f"- {issue['message']}" for issue in issues)
        for appId, issues in issuesById.items()
    }
    runPass(
        toPass,
        flagged,
        lambda app: {
            **researchApp(app, llmClient, toolbox, notesById.get(app["id"], "")),
            "reResearchedFrom": fromPass,
        },
        lambda result: f"re-researched, model {result['model']}",
        {"record": None},
    )


def alreadyReResearched(passName, appId):
    """A re-researched result is never overwritten by a copy of the first-pass record."""
    path = resultPath(passName, appId)
    return path.exists() and "reResearchedFrom" in json.loads(path.read_text(encoding="utf-8"))


def toApp(result):
    return {key: result[key] for key in ("id", "name", "category", "hint")}


def countDisagreements(result):
    return sum(verdict["verdict"] == "disagree" for verdict in result["verdicts"])


if __name__ == "__main__":
    main()
