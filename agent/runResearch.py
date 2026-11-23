"""Command line entry point for the first research pass.

    python agent/runResearch.py --app Stripe          one app, printed and saved
    python agent/runResearch.py --all                 all 100, skipping apps already saved
    python agent/runResearch.py --ids 1 15 84         chosen apps
"""

import argparse
import json

from dotenv import load_dotenv

from composioToolbox import buildToolbox
from geminiClient import buildLlmClient
from passRunner import runPass
from pipelineConfig import PROJECT_ROOT
from researchAgent import researchApp
from resultStore import loadApps, loadPassResults, selectApps

DEFAULT_PASS_NAME = "pass1"
RESEARCH_FAILURE_FIELDS = {"record": None}


def main():
    arguments = parseArguments()
    load_dotenv(PROJECT_ROOT / ".env")
    toolbox = buildToolbox()
    llmClient = buildLlmClient()
    apps = selectApps(loadApps(), arguments.app, arguments.ids)
    runPass(
        arguments.passName,
        apps,
        lambda app: researchApp(app, llmClient, toolbox),
        describeResearch,
        RESEARCH_FAILURE_FIELDS,
        arguments.redo,
    )
    if arguments.app is not None:
        printRecord(arguments.passName, apps[0]["id"])


def parseArguments():
    parser = argparse.ArgumentParser(description="Research apps and save one record per app.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--app", help="exact app name from data/apps.json")
    target.add_argument("--ids", type=int, nargs="+", help="app ids from data/apps.json")
    target.add_argument("--all", action="store_true", help="every app in data/apps.json")
    parser.add_argument("--passName", default=DEFAULT_PASS_NAME, help="results sub-folder")
    parser.add_argument("--redo", action="store_true", help="re-research apps already saved")
    return parser.parse_args()


def describeResearch(result):
    return (
        f"{len(result['toolCalls'])} tool calls, "
        f"{len(result['validationProblems'])} schema problem(s), model {result['model']}"
    )


def printRecord(passName, appId):
    for result in loadPassResults(passName):
        if result["id"] == appId:
            print(json.dumps(result["record"], indent=2))


if __name__ == "__main__":
    main()
