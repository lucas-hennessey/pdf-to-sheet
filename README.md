# PDF to Sheet

Local Mac app: drop Foundation Directory Online PDF exports into a window, review the
parsed rows, and append them to a private Google Sheet. Parsing happens entirely on your Mac.

## Run

Double-click `run.command`, or run `./build_app.sh` to create `~/Applications/PDF to Sheet.app`
and drag it to the Dock. The app opens at http://127.0.0.1:5757.

## Connect Google

Follow the first-time setup guide in the app's Settings panel (creates a free Google OAuth
client, then sign in). Optionally place that client's JSON next to `app.py` as
`google_client.json` so users only need to sign in. Never commit it.

## Files

- `parser.py` extracts the 20 sheet columns from a PDF
- `sheets.py` Google Sheets access (OAuth, Sheets scope only)
- `app.py` + `templates/index.html` local web UI
- `build_app.sh` builds the Dock app
