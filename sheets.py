"""Google Sheets access (OAuth, runs locally; the token never leaves this Mac)."""
import json
from pathlib import Path

import gspread
from google.auth.exceptions import RefreshError

from parser import HEADERS

APP_DIR = Path.home() / ".pdf-to-sheet"
CONFIG_PATH = APP_DIR / "config.json"
TOKEN_PATH = APP_DIR / "token.json"
# OAuth client: either shipped next to this file by whoever distributes the app, or
# uploaded by the user in Settings (stored in APP_DIR). The bundled one wins.
BUNDLED_CLIENT_PATH = Path(__file__).parent / "google_client.json"
USER_CLIENT_PATH = APP_DIR / "google_client.json"


def client_path():
    for p in (BUNDLED_CLIENT_PATH, USER_CLIENT_PATH):
        if p.exists():
            return p
    return None
# Narrowest scope that can read/append rows (no broad Drive access).
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"sheet_url": "", "tab": ""}


def save_config(sheet_url, tab):
    APP_DIR.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"sheet_url": sheet_url.strip(), "tab": tab.strip()}))


def status():
    cfg = load_config()
    return {
        "client_configured": client_path() is not None,
        "signed_in": TOKEN_PATH.exists(),
        "sheet_url": cfg["sheet_url"],
        "tab": cfg["tab"],
    }


def _client():
    client = client_path()
    if not client:
        raise RuntimeError("Google isn't set up yet. Follow the setup steps in Settings.")
    APP_DIR.mkdir(exist_ok=True)
    # Opens the Google sign-in page in the browser if there is no saved token yet.
    return gspread.oauth(
        scopes=SCOPES,
        credentials_filename=str(client),
        authorized_user_filename=str(TOKEN_PATH),
    )


def sign_in():
    _client()


def sign_out():
    TOKEN_PATH.unlink(missing_ok=True)


def _worksheet():
    cfg = load_config()
    if not cfg["sheet_url"]:
        raise RuntimeError("No Google Sheet set yet. Add its URL in Settings.")
    try:
        book = _client().open_by_url(cfg["sheet_url"])
        return book.worksheet(cfg["tab"]) if cfg["tab"] else book.sheet1
    except RefreshError:
        # Google's test mode expires sign-ins after 7 days.
        sign_out()
        raise RuntimeError("Your Google sign-in has expired. Click 'Sign in with Google' in Settings.")
    except gspread.exceptions.WorksheetNotFound:
        raise RuntimeError(f"There is no tab named \"{cfg['tab']}\" in that sheet.")
    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.NoValidUrlKeyFound):
        raise RuntimeError("Couldn't open that sheet. Check the URL, and that the Google account "
                           "you signed in with can edit it.")
    except gspread.exceptions.APIError as e:
        raise RuntimeError(f"Google refused the request: {e}")


def test_connection():
    ws = _worksheet()
    return f"{ws.spreadsheet.title} / {ws.title}"


def append_rows(rows, allow_duplicates=False):
    """Append rows (dicts keyed by HEADERS). Returns (added, skipped_names)."""
    ws = _worksheet()
    existing = ws.get_all_values()
    if not existing or not any(existing[0]):
        ws.update(range_name="A1", values=[HEADERS], value_input_option="RAW")
        existing = [HEADERS]
    # Match on Foundation Name (column A in the sheet, case-insensitive).
    seen = {r[0].strip().lower() for r in existing[1:] if r and r[0].strip()}
    to_add, skipped = [], []
    for row in rows:
        name = str(row.get("Foundation Name", "")).strip()
        if name.lower() in seen and not allow_duplicates:
            skipped.append(name)
            continue
        seen.add(name.lower())
        to_add.append([row.get(h, "") for h in HEADERS])
    if to_add:
        # RAW keeps phone numbers/zips as typed instead of letting Sheets reformat them.
        ws.append_rows(to_add, value_input_option="RAW", table_range="A1")
    return len(to_add), skipped
