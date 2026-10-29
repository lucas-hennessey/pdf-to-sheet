# PDF to Sheet

A Mac app that turns Foundation Directory Online PDF exports into rows in your Google Sheet.
Drop PDFs into the window, check the parsed rows, click **Add to Google Sheet**.

- PDFs are read **on your Mac**. Nothing is uploaded anywhere except the final rows going to your own sheet.
- Your sheet stays **private**. The app signs in as you and only asks for Google Sheets access.

## What you need

- A Mac (Apple Silicon or Intel) running macOS 12 or newer
- Python 3.10 or newer. The install script uses it if present, and installs it via [Homebrew](https://brew.sh) if you have that. Otherwise it tells you where to download it.
- A Google account and a Google Sheet you can edit

## Install (about 3 minutes)

1. **Get the code.** Open Terminal and run:

   ```bash
   git clone https://github.com/lucas-hennessey/pdf-to-sheet.git
   cd pdf-to-sheet
   ```

   No GitHub account is needed. If you don't have `git`, macOS will offer to install it the first time you run the command. Alternatively, click **Code > Download ZIP** on the [repo page](https://github.com/lucas-hennessey/pdf-to-sheet), unzip it and `cd` into the folder.

2. **Run the installer:**

   ```bash
   ./install.sh
   ```

   It checks Python, installs the dependencies, builds the app, and opens the folder containing **PDF to Sheet.app** (`~/Applications`).

3. **Add it to the Dock.** Drag **PDF to Sheet** from that folder onto your Dock.

4. **Click it.** The app opens in your browser at http://127.0.0.1:5757.

> Keep the `pdf-to-sheet` folder where it is. The app points at it. If you move the folder, run `./install.sh` again from the new location.

## Connect your Google Sheet (first launch only)

The first time you open the app, **Settings** opens with a step-by-step guide. In short:

1. Create a free Google Cloud project and turn on the Google Sheets API (no billing needed).
2. Create a **Desktop app** OAuth client and download its JSON file.
3. In the app: choose that JSON file, click **Sign in with Google**, then paste your sheet's URL and tab name and click **Save & test connection**.

Google will say "Google hasn't verified this app". That's expected for your own app: click **Advanced** > **Go to PDF to Sheet (unsafe)**.

While the app is in Google's testing mode, the sign-in expires every 7 days. The app will tell you when that happens, and you just click **Sign in with Google** again.

## Using it

1. Drag one or more PDFs onto the drop area (or click it to choose files).
2. Check the table. Blank cells are highlighted, and every cell is editable.
3. Click **Add to Google Sheet**. Foundations already in the sheet (matched by name) are skipped unless you tick the checkbox.

The sheet's columns are: Foundation Name, Address 1, Address 2, City, State, Zip, Average Grant Amount, Subjects, Population Groups, Geographic Focus, Limitations, Application Process, Contact Name, Contact Address 1, Contact Address 2, Contact City, Contact State, Contact Zip, Contact Phone, Contact Email. An empty sheet gets these headers automatically.

Notes:
- **Average Grant Amount** is the mean of the grants listed in the PDF's Grants table (usually only the first 5).
- Scanned (image-only) PDFs aren't supported; the PDFs must contain real text.

## Quitting, updating, uninstalling

- **Quit:** right-click the Dock icon > Quit. Closing the browser tab does not stop the app.
- **Update:** when a new version is out, a banner appears at the top of the app: click **Update now**. The app downloads the update, installs anything new it needs, restarts itself and reloads. Your Google sign-in and sheet settings are kept. (It checks GitHub when the app opens, so it needs an internet connection.)
- **Updating from a version older than 1.1.0:** those don't have the banner. Update once by hand: `cd pdf-to-sheet && git pull && ./install.sh` (or download the ZIP again, replace the folder and run `./install.sh`). After that, updates are one click.
- **If an update fails:** the banner shows the reason. The usual cause is local edits to the code, which block `git pull`; undo them with `git checkout .` and try again.
- **Uninstall:** delete `~/Applications/PDF to Sheet.app`, the `pdf-to-sheet` folder, and `~/.pdf-to-sheet` (your saved settings and Google sign-in).

## Troubleshooting

| Problem | Fix |
|---|---|
| macOS says the app can't be opened | Right-click the app > **Open** > **Open** (only needed once). |
| Nothing opens when I click the icon | Check `~/.pdf-to-sheet/app.log`, then try `./run.command` in the folder. |
| "Access blocked" when signing in | Add your Gmail address under **Audience > Test users** in Google Cloud (setup step 5). |
| "Your Google sign-in has expired" | Click **Sign in with Google** in Settings. |
| "Couldn't open that sheet" | Check the URL, and that the account you signed in with can edit the sheet. |
| Port 5757 already in use | Quit the app from the Dock (or Activity Monitor) and try again. |
| A field comes back blank | The PDF may not contain it (for example, many have no contact name or email). Fill it in the preview table. |

## For developers

- `parser.py` extracts the 20 sheet columns from a PDF (PyMuPDF)
- `sheets.py` Google Sheets access (OAuth, Sheets scope only)
- `app.py` and `templates/index.html` the local web UI (Flask, bound to 127.0.0.1 only)
- `updater.py` the in-app update check and installer. **To release an update:** bump the number in `VERSION` and push to `main`; open copies of the app will show the banner. Git clones update with `git pull`, ZIP installs by re-downloading the branch.
- `install.sh` from-scratch setup; `build_app.sh` builds the Dock app; `run.command` runs without the Dock app
- To skip the Google Cloud steps for other users, put your own OAuth client JSON next to `app.py` as `google_client.json`; users then only click **Sign in**. It's git-ignored. Never commit it.
