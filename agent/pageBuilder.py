"""Builds docs/index.html and docs/results.json from the saved passes.

    python agent/pageBuilder.py --firstPass pass1 --finalPass pass2

Every number on the page is read from the data embedded here; none is typed into the template.
"""

import argparse
import json
from datetime import date

from pipelineConfig import PROJECT_ROOT
from resultStore import loadApps, loadPassResults

# GitHub Pages serves a branch's /docs folder, so the built page lives there.
SITE_DIR = PROJECT_ROOT / "docs"
TEMPLATE_PATH = PROJECT_ROOT / "agent" / "pageTemplate.html"
DATA_PLACEHOLDER = "__SITE_DATA__"
REPO_PLACEHOLDER = "__REPO_URL__"
DEFAULT_REPO_URL = "https://github.com/OWNER/composio-app-research"


def main():
    parser = argparse.ArgumentParser(description="Build the case-study page.")
    parser.add_argument("--firstPass", required=True)
    parser.add_argument("--finalPass", required=True)
    parser.add_argument("--repoUrl", default=DEFAULT_REPO_URL)
    arguments = parser.parse_args()
    siteData = buildSiteData(arguments.firstPass, arguments.finalPass)
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "results.json").write_text(json.dumps(siteData, indent=1), encoding="utf-8")
    embedded = json.dumps(siteData).replace("</", "<\\/")
    page = TEMPLATE_PATH.read_text(encoding="utf-8")
    page = page.replace(DATA_PLACEHOLDER, embedded).replace(REPO_PLACEHOLDER, arguments.repoUrl)
    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")
    print(f"docs/index.html written, {len(page) // 1024} KB, {len(siteData['apps'])} apps")


def buildSiteData(firstPass, finalPass):
    firstById = byId(loadPassResults(firstPass))
    finalById = byId(loadPassResults(finalPass))
    evidenceById = byId(loadPassResults(firstPass + "Evidence"))
    finalEvidenceById = byId(loadPassResults(finalPass + "Evidence"))
    issuesById = byId(loadPassResults(firstPass + "Issues"))
    catalogById = byId(loadPassResults(firstPass + "Catalog"))
    apps = []
    for app in loadApps():
        appId = app["id"]
        final = finalById.get(appId) or firstById.get(appId)
        apps.append(
            {
                **app,
                "record": final["record"] if final else None,
                "error": final.get("error") if final else "not researched in time",
                "firstRecord": firstById[appId]["record"] if appId in firstById else None,
                "reResearched": bool(final and final.get("reResearchedFrom")),
                "model": final.get("model") if final else None,
                "firstEvidence": evidenceById.get(appId, {}).get("checks", []),
                "finalEvidence": finalEvidenceById.get(appId, {}).get("checks", []),
                "issues": issuesById.get(appId, {}).get("issues", []),
                "catalog": catalogById.get(appId),
            }
        )
    return {
        "built": date.today().isoformat(),
        "apps": apps,
        "patterns": readJson("patterns.json"),
        "scores": {
            name: readJson(f"scores/{name}.json") for name in (firstPass, finalPass)
        },
        "gold": goldSummary(),
        "passes": {"first": firstPass, "final": finalPass},
    }


def goldSummary():
    gold = readJson("goldSample.json")
    return {
        "apps": [entry["name"] for entry in gold],
        "cellsConfident": sum(len(entry["confidentFields"]) for entry in gold),
        "quoteChecks": countStatuses(gold),
        "labelSource": gold[0]["labelSource"],
    }


def countStatuses(gold):
    counts = {}
    for entry in gold:
        for check in entry["quoteChecks"]:
            counts[check["status"]] = counts.get(check["status"], 0) + 1
    return counts


def byId(items):
    return {item["id"]: item for item in items}


def readJson(relativePath):
    path = PROJECT_ROOT / "data" / relativePath
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
