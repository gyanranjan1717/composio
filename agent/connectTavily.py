"""One-time setup: registers the Tavily API key with Composio so the agent can search.

    python agent/connectTavily.py

Safe to run again: it does nothing if an active Tavily connection already exists.
"""

import os

from composio import Composio
from dotenv import load_dotenv

from pipelineConfig import COMPOSIO_USER_ID, PROJECT_ROOT, SEARCH_TOOLKIT

API_KEY_SCHEME = "API_KEY"
# The field name Composio's Tavily toolkit declares for the key.
TAVILY_KEY_FIELD = "generic_api_key"
ACTIVE_STATUS = "ACTIVE"


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
    existing = composio.connected_accounts.list(
        toolkit_slugs=[SEARCH_TOOLKIT], user_ids=[COMPOSIO_USER_ID], statuses=[ACTIVE_STATUS]
    )
    if existing.items:
        print(f"Already connected: {existing.items[0].id}")
        return
    authConfig = composio.auth_configs.create(
        SEARCH_TOOLKIT,
        options={"type": "use_custom_auth", "auth_scheme": API_KEY_SCHEME, "credentials": {}},
    )
    request = composio.connected_accounts.initiate(
        COMPOSIO_USER_ID,
        authConfig.id,
        config={
            "auth_scheme": API_KEY_SCHEME,
            "val": {TAVILY_KEY_FIELD: os.environ["TAVILY_API_KEY"]},
        },
    )
    print(f"Connected: {request.id} status={request.status}")


if __name__ == "__main__":
    main()
