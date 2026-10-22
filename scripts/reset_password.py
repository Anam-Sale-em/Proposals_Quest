"""Reset a user's password (for the app's owner).

  python scripts/reset_password.py <username>

Works on whichever account store the app uses: the Google Sheet at USERS_SHEET_URL, or the
local accounts file. The user's jobs and projects stay, because they're keyed by user id."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal_v2.auth import AuthError, make_user_store, reset_password  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return
    pw = getpass.getpass("New password: ")
    if pw != getpass.getpass("Again: "):
        print("The two passwords don't match.")
        return
    try:
        rec = reset_password(make_user_store(), sys.argv[1], pw)
        print(f"Password reset for {rec.username}.")
    except AuthError as e:
        print(e)


if __name__ == "__main__":
    main()
