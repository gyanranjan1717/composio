"""Builds data/goldSample.json from the independent labellers' files.

    python agent/goldAssembler.py

Each labeller file holds labels plus a verbatim quote per field. Every quote is re-checked
against its live page with the same deterministic checker used on the research agent, and
the outcome is stored beside the label, so a gold label with unverified evidence is visible
as such instead of being trusted blindly.
"""

import json

from appSchema import ENUM_FIELDS, SCORED_FIELDS, findAuthProblems
from evidenceChecker import checkEntry
from pipelineConfig import GOLD_SAMPLE_PATH, PROJECT_ROOT

LABELLER_DIR = PROJECT_ROOT / ".agents"
LABELLER_FILE_PATTERN = "goldLabeller*/labels.json"
SAMPLE_APPS_PATH = PROJECT_ROOT / "data" / "goldSampleApps.json"
GOLD_REVIEW_PATH = PROJECT_ROOT / "data" / "goldReview.json"
LABEL_SOURCE = "aiLabeller"


def main():
    sampleApps = json.loads(SAMPLE_APPS_PATH.read_text(encoding="utf-8"))
    labelledById = loadLabellerOutput()
    missing = [app["name"] for app in sampleApps if app["id"] not in labelledById]
    if missing:
        raise SystemExit(f"No labels yet for: {missing}")
    reviewsById = loadReviews()
    gold = [
        assembleEntry(app, labelledById[app["id"]], reviewsById.get(app["id"], []))
        for app in sampleApps
    ]
    GOLD_SAMPLE_PATH.write_text(json.dumps(gold, indent=2), encoding="utf-8")
    printSummary(gold)


def loadLabellerOutput():
    labelledById = {}
    for path in sorted(LABELLER_DIR.glob(LABELLER_FILE_PATTERN)):
        for item in json.loads(path.read_text(encoding="utf-8")):
            labelledById[item["id"]] = item
    return labelledById


def assembleEntry(app, labelled, reviews):
    label = dict(labelled["label"])
    confidentFields = [
        fieldName for fieldName in SCORED_FIELDS if fieldName not in labelled["unsureFields"]
    ]
    for review in reviews:
        label[review["field"]] = review["value"]
        if review["confident"] and review["field"] not in confidentFields:
            confidentFields.append(review["field"])
        if not review["confident"] and review["field"] in confidentFields:
            confidentFields.remove(review["field"])
    return {
        **app,
        "label": label,
        "labelSource": LABEL_SOURCE,
        "labelProblems": findLabelProblems(label),
        "unsureFields": labelled["unsureFields"],
        "confidentFields": sorted(confidentFields),
        "quoteChecks": [checkEntry(entry) for entry in labelled["evidence"]],
        "reviews": reviews,
    }


def loadReviews():
    """Reviewer decisions on single gold cells, kept in a file so the gold set is reproducible."""
    if not GOLD_REVIEW_PATH.exists():
        return {}
    reviewsById = {}
    for review in json.loads(GOLD_REVIEW_PATH.read_text(encoding="utf-8")):
        reviewsById.setdefault(review["id"], []).append(review)
    return reviewsById


def findLabelProblems(label):
    problems = findAuthProblems(label["authMethods"])
    for fieldName in SCORED_FIELDS:
        if fieldName == "authMethods":
            continue
        if label[fieldName] not in ENUM_FIELDS[fieldName]:
            problems.append(f"{fieldName}: '{label[fieldName]}' is not an allowed value")
    return problems


def printSummary(gold):
    statusCounts = {}
    for entry in gold:
        for check in entry["quoteChecks"]:
            statusCounts[check["status"]] = statusCounts.get(check["status"], 0) + 1
    confidentCells = sum(len(entry["confidentFields"]) for entry in gold)
    print(f"{len(gold)} gold entries written to {GOLD_SAMPLE_PATH.name}")
    print("quote checks:", statusCounts)
    print(f"confident cells: {confidentCells} of {len(gold) * len(SCORED_FIELDS)}")
    for entry in gold:
        if entry["labelProblems"]:
            print(f"  label problem #{entry['id']} {entry['name']}: {entry['labelProblems']}")


if __name__ == "__main__":
    main()
