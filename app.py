"""Local drag-and-drop app: parse foundation PDFs and append them to a Google Sheet."""
import json
import os
import tempfile
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import sheets
import updater
from parser import HEADERS, parse_pdf

PORT = 5757
app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", headers=HEADERS, version=updater.local_version())


@app.get("/api/status")
def status():
    return jsonify(sheets.status())


@app.post("/api/settings")
def settings():
    data = request.get_json(force=True)
    sheets.save_config(data.get("sheet_url", ""), data.get("tab", ""))
    return jsonify(sheets.status())


@app.post("/api/client")
def client_upload():
    f = request.files.get("file")
    if not f:
        return jsonify(error="No file received."), 400
    raw = f.read()
    try:
        data = json.loads(raw)
        ok = "installed" in data and data["installed"].get("client_id")
    except (ValueError, AttributeError):
        ok = False
    if not ok:
        return jsonify(error="That isn't the right file. In step 6 choose application type "
                             "'Desktop app' and download its JSON."), 400
    sheets.APP_DIR.mkdir(exist_ok=True)
    sheets.USER_CLIENT_PATH.write_bytes(raw)
    sheets.sign_out()  # new client -> any old sign-in is no longer valid
    return jsonify(sheets.status())


@app.get("/api/update/check")
def update_check():
    return jsonify(updater.check())


@app.post("/api/update/apply")
def update_apply():
    try:
        version = updater.apply()
    except Exception as e:
        return jsonify(error=str(e)), 400
    # Restart after the response has been sent so the page can wait for the new server.
    threading.Timer(0.5, updater.restart).start()
    return jsonify(ok=True, version=version)


@app.post("/api/signin")
def signin():
    try:
        sheets.sign_in()  # blocks until the user finishes Google's consent page
        return jsonify(sheets.status())
    except Exception as e:
        return jsonify(error=str(e)), 400


@app.post("/api/signout")
def signout():
    sheets.sign_out()
    return jsonify(sheets.status())


@app.post("/api/test")
def test():
    try:
        return jsonify(ok=True, name=sheets.test_connection(), **sheets.status())
    except Exception as e:  # surface auth/permission/URL problems in the UI
        return jsonify(ok=False, error=str(e)), 400


@app.post("/api/parse")
def parse():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in request.files.getlist("files"):
            name = Path(f.filename).name
            if not name.lower().endswith(".pdf"):
                results.append({"filename": name, "error": "Not a PDF."})
                continue
            path = Path(tmp) / name
            f.save(path)
            try:
                row, warnings = parse_pdf(path)
                results.append({"filename": name, "row": row, "warnings": warnings})
            except Exception as e:
                results.append({"filename": name, "error": f"Could not read PDF: {e}"})
    return jsonify(results)


@app.post("/api/send")
def send():
    data = request.get_json(force=True)
    try:
        added, skipped = sheets.append_rows(data["rows"], data.get("allow_duplicates", False))
        return jsonify(ok=True, added=added, skipped=skipped)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400


if __name__ == "__main__":
    if not os.environ.get("PTS_RESTARTED"):  # an update restart reuses the tab that's already open
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    app.run(host="127.0.0.1", port=PORT)  # loopback only: nothing is exposed to the network
