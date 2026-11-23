"""Computes every number the case study states about patterns, from the final records.

    python agent/patternAnalyzer.py --passName final

No model is involved: these are counts and cross-tabs over the saved records, so each
headline on the page can be traced to this file and re-run.
"""

import argparse
import json
from collections import Counter

from pipelineConfig import PROJECT_ROOT
from resultStore import loadPassResults

PATTERNS_PATH = PROJECT_ROOT / "data" / "patterns.json"
CATALOG_SUFFIX = "Catalog"
SELF_SERVE_LEVELS = ("selfServeFree", "selfServeTrial")
OUTREACH_LEVELS = ("partnerGated", "adminApproval")
NOT_IN_CATALOG = "notInCatalog"


def main():
    parser = argparse.ArgumentParser(description="Count patterns across the final records.")
    parser.add_argument("--passName", required=True)
    parser.add_argument("--catalogPass", required=True, help="pass whose catalog check to use")
    arguments = parser.parse_args()
    results = loadPassResults(arguments.passName)
    catalogById = {
        item["id"]: item for item in loadPassResults(arguments.catalogPass + CATALOG_SUFFIX)
    }
    patterns = buildPatterns(results, catalogById)
    PATTERNS_PATH.write_text(json.dumps(patterns, indent=2), encoding="utf-8")
    print(json.dumps(patterns["totals"], indent=2))


def buildPatterns(results, catalogById):
    answered = [result for result in results if result["record"] is not None]
    records = [result["record"] for result in answered]
    return {
        "totals": {
            "apps": len(results),
            "withRecord": len(answered),
            "withoutRecord": [result["name"] for result in results if result["record"] is None],
        },
        "authMethodCounts": countAuthMethods(records),
        "authCombinationCounts": countValues(
            "+".join(sorted(record["authMethods"])) for record in records
        ),
        "accessLevelCounts": countField(records, "accessLevel"),
        "apiTypeCounts": countField(records, "apiType"),
        "existingMcpCounts": countField(records, "existingMcp"),
        "buildableCounts": countField(records, "buildable"),
        "mainBlockerCounts": countField(records, "mainBlocker"),
        "oauthAppReviewRequired": sum(record["oauthAppReviewRequired"] for record in records),
        "byCategory": buildCategoryTable(answered),
        "easyWins": listApps(answered, isEasyWin),
        "needsOutreach": listApps(answered, needsOutreach),
        "notBuildable": listApps(answered, lambda record: record["buildable"] == "no"),
        "composioCatalog": buildCatalogView(answered, catalogById),
    }


def countAuthMethods(records):
    counts = Counter(method for record in records for method in record["authMethods"])
    return dict(counts.most_common())


def countField(records, fieldName):
    return countValues(record[fieldName] for record in records)


def countValues(values):
    return dict(Counter(values).most_common())


def buildCategoryTable(answered):
    table = {}
    for result in answered:
        row = table.setdefault(
            result["category"],
            {"apps": 0, "accessLevel": Counter(), "buildable": Counter(), "existingMcp": Counter()},
        )
        row["apps"] += 1
        for fieldName in ("accessLevel", "buildable", "existingMcp"):
            row[fieldName][result["record"][fieldName]] += 1
    return {
        category: {
            **{key: dict(value) if isinstance(value, Counter) else value for key, value in row.items()},
            "selfServe": sum(row["accessLevel"][level] for level in SELF_SERVE_LEVELS),
        }
        for category, row in table.items()
    }


def isEasyWin(record):
    return record["buildable"] == "yes" and record["accessLevel"] in SELF_SERVE_LEVELS


def needsOutreach(record):
    return record["accessLevel"] in OUTREACH_LEVELS


def listApps(answered, predicate):
    return [result["name"] for result in answered if predicate(result["record"])]


def buildCatalogView(answered, catalogById):
    """Which apps Composio already has, and which easy wins it does not have yet."""
    missing = [
        result for result in answered if catalogById[result["id"]]["status"] == NOT_IN_CATALOG
    ]
    return {
        "alreadyInCatalog": len(answered) - len(missing),
        "notInCatalog": [result["name"] for result in missing],
        "notInCatalogButEasyWin": listApps(missing, isEasyWin),
    }


if __name__ == "__main__":
    main()
