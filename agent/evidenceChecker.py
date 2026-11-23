"""Deterministic check of the agent's evidence: is each quote really on the page it cites?

No model is involved. Each cited URL is fetched again and the quote is searched for in the
page text, comparing letters and digits only so that spacing, punctuation and typographic
quotes cannot cause a false miss or a false hit on different words.

    python agent/evidenceChecker.py --passName pass1
"""

import argparse
import re
from concurrent.futures import ThreadPoolExecutor

from pageFetcher import fetchPage
from resultStore import loadPassResults, saveResult

QUOTE_FOUND = "quoteFound"
QUOTE_NOT_FOUND = "quoteNotFound"
PAGE_UNREADABLE = "pageUnreadable"
# A page that yields less text than this is a JavaScript shell or an error page, so a missing
# quote there says nothing about the agent; it goes to the browser check instead.
MIN_READABLE_CHARS = 400
# Shorter quotes match by coincidence too easily to count as evidence.
MIN_QUOTE_CHARS = 25
EVIDENCE_SUFFIX = "Evidence"
PARALLEL_FETCHES = 16
NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def main():
    parser = argparse.ArgumentParser(description="Check every cited quote against its page.")
    parser.add_argument("--passName", required=True)
    arguments = parser.parse_args()
    counts = {QUOTE_FOUND: 0, QUOTE_NOT_FOUND: 0, PAGE_UNREADABLE: 0}
    results = [
        result for result in loadPassResults(arguments.passName) if result["record"] is not None
    ]
    with ThreadPoolExecutor(max_workers=PARALLEL_FETCHES) as pool:
        allChecks = list(pool.map(lambda result: checkRecord(result["record"]), results))
    for result, checks in zip(results, allChecks):
        saveResult(
            arguments.passName + EVIDENCE_SUFFIX,
            {"id": result["id"], "name": result["name"], "checks": checks},
        )
        for check in checks:
            counts[check["status"]] += 1
    print(counts)


def checkRecord(record):
    return [checkEntry(entry) for entry in record["evidence"]]


def checkEntry(entry):
    check = {"field": entry["field"], "url": entry["url"], "quote": entry["quote"]}
    page = fetchPage(entry["url"])
    if page["error"] is not None or len(page["text"]) < MIN_READABLE_CHARS:
        return {**check, "status": PAGE_UNREADABLE, "detail": page["error"] or "too little text"}
    if quoteAppears(entry["quote"], page["text"]):
        return {**check, "status": QUOTE_FOUND, "detail": ""}
    return {**check, "status": QUOTE_NOT_FOUND, "detail": "quote is not on the cited page"}


def quoteAppears(quote, pageText):
    normalisedQuote = normalise(quote)
    if len(normalisedQuote) < MIN_QUOTE_CHARS:
        return False
    return normalisedQuote in normalise(pageText)


def normalise(text):
    return NON_ALPHANUMERIC.sub("", text.lower())


if __name__ == "__main__":
    main()
