"""Fetches a public web page and returns its readable text.

The research agent and the evidence checker both read pages through this one function, so a
quote the agent copied is checked against the same text extraction it saw.
"""

import hashlib
import json

import requests
from bs4 import BeautifulSoup

from pipelineConfig import PAGE_CACHE_DIR

REQUEST_TIMEOUT_SECONDS = 25
# Several docs sites return 403 to the default python-requests agent string.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)
NON_CONTENT_TAGS = ("script", "style", "noscript", "svg", "template")
HTTP_OK = 200


def fetchPage(url):
    """Return {url, finalUrl, status, text, error}; never raises for a bad page."""
    cachePath = PAGE_CACHE_DIR / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")
    if cachePath.exists():
        return json.loads(cachePath.read_text(encoding="utf-8"))
    page = downloadPage(url)
    if page["error"] is None:
        PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cachePath.write_text(json.dumps(page), encoding="utf-8")
    return page


def downloadPage(url):
    page = {"url": url, "finalUrl": url, "status": None, "text": "", "error": None}
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as error:
        page["error"] = f"{type(error).__name__}: {error}"
        return page
    page["finalUrl"] = response.url
    page["status"] = response.status_code
    if response.status_code != HTTP_OK:
        page["error"] = f"HTTP {response.status_code}"
        return page
    page["text"] = extractText(response.text)
    return page


def extractText(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NON_CONTENT_TAGS):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())
