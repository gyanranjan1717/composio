"""Runs one pipeline step over many apps in parallel, saving one result file per app.

Shared by the research, verifier and re-research steps so all three resume the same way and
none can lose an app: a step that raises is saved as a failed result, not dropped.
"""

from concurrent.futures import ThreadPoolExecutor

from pipelineConfig import MAX_PARALLEL_APPS
from resultStore import hasResult, saveResult


def runPass(passName, apps, produceOutcome, describeOutcome, failureFields, redo=False):
    """Call produceOutcome(app) for each app not yet saved under passName."""
    pending = [app for app in apps if redo or not hasResult(passName, app["id"])]
    print(f"[{passName}] {len(pending)} app(s) to do, {len(apps) - len(pending)} already saved")

    def runOne(app):
        try:
            result = {**app, **produceOutcome(app)}
        # Whatever went wrong for this app (API error, bad JSON, quota), the others must
        # still run and this one must show up in the output as failed.
        except Exception as error:
            result = {**app, **failureFields, "error": f"{type(error).__name__}: {error}"}
            print(f"FAILED  #{app['id']} {app['name']}: {result['error'][:200]}")
        else:
            print(f"done    #{app['id']} {app['name']}: {describeOutcome(result)}")
        saveResult(passName, result)

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_APPS) as pool:
        list(pool.map(runOne, pending))
