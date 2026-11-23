"""Cross-checks the agent's auth answer against Composio's own toolkit catalog.

    python agent/composioCatalogCheck.py --passName pass1

Where Composio already ships a toolkit for an app, the auth schemes that toolkit uses are an
independent source the research agent never saw. A toolkit may implement only some of a
vendor's auth methods, so the check runs one way: every scheme Composio uses should appear
in the agent's authMethods. A scheme the agent lists but Composio does not is not an error.
"""

import argparse
import json
import os
import re

from composio import Composio
from dotenv import load_dotenv

from pipelineConfig import PROJECT_ROOT
from resultStore import loadApps, loadPassResults, saveResult

CATALOG_PATH = PROJECT_ROOT / "data" / "composioCatalog.json"
CATALOG_PAGE_SIZE = 1000
CATALOG_SUFFIX = "Catalog"
NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
# Composio scheme names mapped onto the rubric's authMethods values.
SCHEME_TO_AUTH_METHOD = {
    "OAUTH2": "oauth2",
    "S2S_OAUTH2": "oauth2",
    "DCR_OAUTH": "oauth2",
    "OAUTH1": "other",
    "SAML": "other",
    "API_KEY": "apiKey",
    "BEARER_TOKEN": "apiKey",
    "BASIC": "basic",
    "BASIC_WITH_JWT": "jwt",
    "GOOGLE_SERVICE_ACCOUNT": "jwt",
    "SERVICE_ACCOUNT": "jwt",
    "NO_AUTH": "none",
}
# Apps whose Composio toolkit slug is not simply the app name with punctuation removed.
# Matched by hand from the catalog on 2026-11-23. Near-misses that are a different product
# (Salesforce Commerce Cloud vs "salesforce", Mermaid CLI vs "mermaid_chart_mcp",
# Amazon Selling Partner vs "amazon") are deliberately left unmatched.
APP_SLUG_ALIASES = {
    "Zoho CRM": "zoho",
    "Lark (Larksuite)": "lark",
    "WhatsApp Business": "whatsapp",
    "Threads (Meta)": "threads",
    "MongoDB Atlas": "mongodb",
    "Monday.com": "monday",
    "Pylon": "pylon_mcp",
    "Netlify": "netlify_mcp",
    "Otter AI": "otter_ai_mcp",
    "Devin": "devin_mcp",
}
MCP_SLUG_SUFFIX = "_mcp"
MCP_NONE = "none"
IN_CATALOG_AGREES = "agrees"
IN_CATALOG_DISAGREES = "disagrees"
NOT_IN_CATALOG = "notInCatalog"
NO_RECORD = "noRecord"


def main():
    parser = argparse.ArgumentParser(description="Compare a pass with Composio's catalog.")
    parser.add_argument("--passName", required=True)
    parser.add_argument("--refresh", action="store_true", help="download the catalog again")
    arguments = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    catalog = loadCatalog(arguments.refresh)
    recordsById = {result["id"]: result["record"] for result in loadPassResults(arguments.passName)}
    counts = {}
    for app in loadApps():
        check = checkApp(app, catalog, recordsById.get(app["id"]))
        saveResult(arguments.passName + CATALOG_SUFFIX, check)
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    print(counts)


def loadCatalog(refresh):
    if CATALOG_PATH.exists() and not refresh:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
    catalog, cursor = {}, None
    while True:
        page = composio.toolkits.list(limit=CATALOG_PAGE_SIZE, cursor=cursor)
        for item in page.items:
            catalog[item.slug] = {"name": item.name, "authSchemes": item.auth_schemes}
        cursor = page.next_cursor
        if not cursor:
            break
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")
    return catalog


def checkApp(app, catalog, record):
    check = {"id": app["id"], "name": app["name"], "toolkitSlug": findToolkitSlug(app, catalog)}
    check["mcpToolkitSlug"] = findMcpToolkitSlug(app, catalog, check["toolkitSlug"])
    # Composio wrapping a vendor MCP server contradicts an agent answer of "no MCP exists".
    check["mcpContradiction"] = (
        check["mcpToolkitSlug"] is not None
        and record is not None
        and record["existingMcp"] == MCP_NONE
    )
    if check["toolkitSlug"] is None:
        return {**check, "status": NOT_IN_CATALOG, "composioAuthMethods": [], "missing": []}
    schemes = catalog[check["toolkitSlug"]]["authSchemes"]
    composioMethods = sorted({SCHEME_TO_AUTH_METHOD.get(scheme, "other") for scheme in schemes})
    check["composioAuthMethods"] = composioMethods
    if record is None:
        return {**check, "status": NO_RECORD, "missing": composioMethods}
    missing = [method for method in composioMethods if method not in record["authMethods"]]
    status = IN_CATALOG_DISAGREES if missing else IN_CATALOG_AGREES
    return {**check, "status": status, "missing": missing}


def findToolkitSlug(app, catalog):
    if app["name"] in APP_SLUG_ALIASES:
        return APP_SLUG_ALIASES[app["name"]]
    wanted = normalise(app["name"])
    for slug, toolkit in catalog.items():
        if wanted in (normalise(slug), normalise(toolkit["name"])):
            return slug
    return None


def findMcpToolkitSlug(app, catalog, toolkitSlug):
    if toolkitSlug is not None and toolkitSlug.endswith(MCP_SLUG_SUFFIX):
        return toolkitSlug
    wanted = normalise(app["name"]) + normalise(MCP_SLUG_SUFFIX)
    for slug in catalog:
        if normalise(slug) == wanted:
            return slug
    return None


def normalise(text):
    return NON_ALPHANUMERIC.sub("", text.lower())


if __name__ == "__main__":
    main()
