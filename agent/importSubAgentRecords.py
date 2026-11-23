"""Adds records written by parallel Claude sub-agents to a pass.

    python agent/importSubAgentRecords.py --passName pass1
    python agent/importSubAgentRecords.py --passName pass2 --reResearch --fromPass pass1

First form: fills apps the Gemini run did not finish (the free-tier Gemini key was too slow to
finish all 100 apps before the deadline). An app the Gemini run already finished is never
overwritten.
Second form: stores sub-agent re-research of apps the checks flagged, after the Gemini
re-research failed on 503 errors. Those results replace the carried first-pass record.

Every imported result is tagged with the model that produced it so the page can say which
apps were researched by which model.
"""

import argparse
import json

from appSchema import validateRecord
from pipelineConfig import PROJECT_ROOT
from resultStore import hasResult, loadApps, saveResult

RESEARCH_PATTERN = "research*/records.json"
RERESEARCH_PATTERN = "reresearch*/records.json"
SUB_AGENT_MODEL = "claude-haiku-5-5 (sub-agent)"


def main():
    parser = argparse.ArgumentParser(description="Import sub-agent records into a pass.")
    parser.add_argument("--passName", required=True)
    parser.add_argument("--reResearch", action="store_true")
    parser.add_argument("--fromPass", default=None)
    arguments = parser.parse_args()
    appsById = {app["id"]: app for app in loadApps()}
    pattern = RERESEARCH_PATTERN if arguments.reResearch else RESEARCH_PATTERN
    imported, kept = [], []
    for path in sorted((PROJECT_ROOT / ".agents").glob(pattern)):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if not arguments.reResearch and hasResult(arguments.passName, item["id"]):
                kept.append(item["name"])
                continue
            result = buildResult(appsById[item["id"]], item["record"])
            if arguments.reResearch:
                result["reResearchedFrom"] = arguments.fromPass
            saveResult(arguments.passName, result)
            imported.append(item["name"])
    print(f"imported {len(imported)}: {imported}")
    print(f"kept existing Gemini result for {len(kept)}: {kept}")


def buildResult(app, record):
    return {
        **app,
        "record": record,
        "validationProblems": validateRecord(record),
        "toolCalls": [],
        "usage": {},
        "hitTurnLimit": False,
        "model": SUB_AGENT_MODEL,
    }


if __name__ == "__main__":
    main()
