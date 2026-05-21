import argparse
import sys
import auth


def cmd_login(_args):
    token = auth.get_token()
    if token:
        profile = auth.get_profile(token)
        print(f"Already logged in as {profile['displayName']} ({profile['mail'] or profile['userPrincipalName']})")
        return

    print("Logging in to Microsoft Teams...")
    try:
        token = auth.login()
    except RuntimeError as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)

    profile = auth.get_profile(token)
    print(f"Logged in as {profile['displayName']} ({profile['mail'] or profile['userPrincipalName']})")


def cmd_logout(_args):
    auth.logout()
    print("Logged out.")


def cmd_whoami(_args):
    token = auth.get_token()
    if not token:
        print("Not logged in. Run: python main.py login", file=sys.stderr)
        sys.exit(1)

    profile = auth.get_profile(token)
    print(f"Name:  {profile['displayName']}")
    print(f"Email: {profile.get('mail') or profile.get('userPrincipalName')}")
    print(f"ID:    {profile['id']}")


def cmd_teams(_args):
    token = auth.get_token()
    if not token:
        print("Not logged in. Run: python main.py login", file=sys.stderr)
        sys.exit(1)

    teams = auth.get_teams(token)
    if not teams:
        print("No teams found.")
        return

    print(f"{'Team Name':<40} ID")
    print("-" * 80)
    for team in teams:
        print(f"{team['displayName']:<40} {team['id']}")


def main():
    parser = argparse.ArgumentParser(description="Microsoft Teams CLI")
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    sub.add_parser("login", help="Log in to Microsoft Teams")
    sub.add_parser("logout", help="Log out and clear cached credentials")
    sub.add_parser("whoami", help="Show the currently logged-in user")
    sub.add_parser("teams", help="List your joined Teams")

    args = parser.parse_args()
    dispatch = {
        "login": cmd_login,
        "logout": cmd_logout,
        "whoami": cmd_whoami,
        "teams": cmd_teams,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
