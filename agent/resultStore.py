"""Reads the app list and reads/writes one JSON result file per app per pass."""

import json

from pipelineConfig import APPS_PATH, RESULTS_DIR

RESULT_FILE_DIGITS = 3


def loadApps():
    return json.loads(APPS_PATH.read_text(encoding="utf-8"))


def selectApps(apps, appName=None, appIds=None):
    if appName is not None:
        matches = [app for app in apps if app["name"].lower() == appName.lower()]
        if not matches:
            raise ValueError(f"No app named '{appName}' in {APPS_PATH.name}")
        return matches
    if appIds is not None:
        return [app for app in apps if app["id"] in appIds]
    return apps


def resultPath(passName, appId):
    return RESULTS_DIR / passName / f"{appId:0{RESULT_FILE_DIGITS}d}.json"


def hasResult(passName, appId):
    """True only for a saved result that succeeded; a saved failure is retried on resume."""
    path = resultPath(passName, appId)
    if not path.exists():
        return False
    saved = json.loads(path.read_text(encoding="utf-8"))
    return "error" not in saved


def saveResult(passName, result):
    path = resultPath(passName, result["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def loadPassResults(passName):
    paths = sorted((RESULTS_DIR / passName).glob("*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]
