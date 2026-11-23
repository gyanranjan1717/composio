"""Scores one research pass against the gold sample, field by field.

    python agent/accuracyScorer.py --passName pass1

A field is right only if it equals the gold label exactly; authMethods is compared as a set,
so a missing or extra method counts as wrong. Gold cells the labeller could not settle from
the docs are not scored, and the number left out is reported beside every accuracy figure. Accuracy is reported separately for the "dev"
half (used to tune the loops) and the "heldOut" half (never used for tuning), because only
the held-out number is an honest estimate for the other 70 apps.
"""

import argparse
import json

from appSchema import SCORED_FIELDS
from pipelineConfig import GOLD_SAMPLE_PATH, SCORES_DIR
from resultStore import loadPassResults

ALL_SPLITS = "all"
NO_ANSWER = "noAnswer"


def main():
    parser = argparse.ArgumentParser(description="Score a pass against the gold sample.")
    parser.add_argument("--passName", required=True)
    arguments = parser.parse_args()
    score = scorePass(arguments.passName)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    scorePath = SCORES_DIR / f"{arguments.passName}.json"
    scorePath.write_text(json.dumps(score, indent=2), encoding="utf-8")
    printScore(score)


def scorePass(passName):
    gold = json.loads(GOLD_SAMPLE_PATH.read_text(encoding="utf-8"))
    # A Claude sub-agent first-pass record is not scored: the same model family wrote the gold
    # labels, so agreement would be inflated. Re-researched records are scored and disclosed.
    recordsById = {
        result["id"]: result["record"]
        for result in loadPassResults(passName)
        if "sub-agent" not in result.get("model", "") or "reResearchedFrom" in result
    }
    # A gold app the pass never finished has no answer to compare; it is left out and counted.
    comparisons = [
        compareField(entry, recordsById[entry["id"]], fieldName)
        for entry in gold
        if recordsById.get(entry["id"]) is not None
        for fieldName in SCORED_FIELDS
        if fieldName in entry["confidentFields"]
    ]
    goldAppsAnswered = sum(recordsById.get(entry["id"]) is not None for entry in gold)
    splits = sorted({entry["split"] for entry in gold})
    return {
        "passName": passName,
        "goldApps": len(gold),
        "goldAppsAnswered": goldAppsAnswered,
        "cellsScored": len(comparisons),
        "cellsExcluded": len(gold) * len(SCORED_FIELDS) - len(comparisons),
        "accuracy": {
            split: summarise([item for item in comparisons if split in (ALL_SPLITS, item["split"])])
            for split in [ALL_SPLITS, *splits]
        },
        "misses": [item for item in comparisons if not item["correct"]],
    }


def compareField(goldEntry, record, fieldName):
    expected = goldEntry["label"][fieldName]
    answered = NO_ANSWER if record is None else record[fieldName]
    return {
        "id": goldEntry["id"],
        "name": goldEntry["name"],
        "split": goldEntry["split"],
        "field": fieldName,
        "expected": expected,
        "answered": answered,
        "correct": normalise(expected) == normalise(answered),
    }


def normalise(value):
    if isinstance(value, list):
        return sorted(value)
    return value


def summarise(comparisons):
    summary = {"overall": ratio(comparisons)}
    for fieldName in SCORED_FIELDS:
        summary[fieldName] = ratio([item for item in comparisons if item["field"] == fieldName])
    return summary


def ratio(comparisons):
    correct = sum(item["correct"] for item in comparisons)
    return {"correct": correct, "total": len(comparisons)}


def printScore(score):
    print(
        f"pass: {score['passName']}  gold apps answered: {score['goldAppsAnswered']}/{score['goldApps']}  "
        f"cells scored: {score['cellsScored']}  excluded (unsure or unanswered): {score['cellsExcluded']}"
    )
    for split, summary in score["accuracy"].items():
        cells = [
            f"{name} {value['correct']}/{value['total']}" for name, value in summary.items()
        ]
        print(f"  {split:8} " + " | ".join(cells))
    print(f"  misses: {len(score['misses'])}")


if __name__ == "__main__":
    main()
