"""Draws the gold sample and builds the page a human uses to label it.

    python agent/goldSampler.py

The sample is three apps per category, drawn with a fixed seed so anyone can reproduce it.
Half the sample ("dev") is used to find failure patterns and tune the verification loops;
the other half ("heldOut") is only scored at the end, so the final accuracy figure is not
inflated by fixes aimed at the apps it is measured on.
"""

import json
import random

from appSchema import ACCESS_LEVELS, API_TYPES, AUTH_METHODS, BLOCKERS, BUILDABLE_VERDICTS, MCP_STATUSES
from pipelineConfig import PROJECT_ROOT, RUBRIC_PATH
from resultStore import loadApps

GOLD_SEED = 20261123
APPS_PER_CATEGORY = 3
SPLIT_NAMES = ("dev", "heldOut")
TEMPLATE_PATH = RUBRIC_PATH.parent / "goldLabellerTemplate.html"
LABELLER_PATH = PROJECT_ROOT / "data" / "goldLabeller.html"
SAMPLE_APPS_PATH = PROJECT_ROOT / "data" / "goldSampleApps.json"
DATA_PLACEHOLDER = "__LABELLER_DATA__"


def main():
    sampleApps = drawSample(loadApps())
    SAMPLE_APPS_PATH.write_text(json.dumps(sampleApps, indent=2), encoding="utf-8")
    labellerData = {
        "apps": sampleApps,
        "rubric": RUBRIC_PATH.read_text(encoding="utf-8"),
        "enums": {
            "authMethods": AUTH_METHODS,
            "accessLevel": ACCESS_LEVELS,
            "apiType": API_TYPES,
            "existingMcp": MCP_STATUSES,
            "buildable": BUILDABLE_VERDICTS,
            "mainBlocker": BLOCKERS,
        },
    }
    # "</" inside the JSON would end the script tag that carries it.
    embedded = json.dumps(labellerData).replace("</", "<\\/")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    LABELLER_PATH.write_text(template.replace(DATA_PLACEHOLDER, embedded), encoding="utf-8")
    splitCounts = {name: sum(app["split"] == name for app in sampleApps) for name in SPLIT_NAMES}
    print(f"{len(sampleApps)} apps sampled, split {splitCounts}")
    print(f"Open {LABELLER_PATH} in a browser to label them.")


def drawSample(apps):
    generator = random.Random(GOLD_SEED)
    categories = sorted({app["category"] for app in apps})
    chosen = []
    for category in categories:
        inCategory = [app for app in apps if app["category"] == category]
        chosen.extend(generator.sample(inCategory, APPS_PER_CATEGORY))
    generator.shuffle(chosen)
    sampleApps = [
        {**app, "split": SPLIT_NAMES[position % len(SPLIT_NAMES)]}
        for position, app in enumerate(chosen)
    ]
    return sorted(sampleApps, key=lambda app: app["id"])


if __name__ == "__main__":
    main()
