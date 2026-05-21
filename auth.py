import json
import os
import msal
import requests

# Public client ID — works for device code flow with Microsoft Graph.
# Replace with your own Azure AD app registration for production use.
CLIENT_ID = os.environ.get("TEAMS_CLIENT_ID", "04b07795-8ddb-461a-bbee-02f9e1bf7b46")
TENANT_ID = os.environ.get("TEAMS_TENANT_ID", "common")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read", "Team.ReadBasic.All", "Channel.ReadBasic.All"]
TOKEN_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".teams_cli_cache.json")


def _build_app() -> msal.PublicClientApplication:
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE) as f:
            cache.deserialize(f.read())
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    return app


def _save_cache(app: msal.PublicClientApplication) -> None:
    if app.token_cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(app.token_cache.serialize())


def login() -> str:
    """Start device code flow. Returns an access token on success."""
    app = _build_app()

    # Reuse cached token if available
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(app)
            return result["access_token"]

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to create device flow: {flow.get('error_description')}")

    print(flow["message"])  # prompts user to visit URL and enter code

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Authentication failed"))

    _save_cache(app)
    return result["access_token"]


def get_token() -> str | None:
    """Return a valid cached token, or None if not logged in."""
    app = _build_app()
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        _save_cache(app)
        return result["access_token"]
    return None


def logout() -> None:
    if os.path.exists(TOKEN_CACHE_FILE):
        os.remove(TOKEN_CACHE_FILE)


def get_profile(token: str) -> dict:
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_teams(token: str) -> list[dict]:
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me/joinedTeams",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("value", [])
