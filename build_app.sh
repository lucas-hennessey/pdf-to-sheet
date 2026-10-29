#!/bin/zsh
# Builds "PDF to Sheet.app" into ~/Applications (drag it to the Dock from there).
# Re-run after moving this project folder, since the app points at this folder.
set -e
PROJECT="$(cd "$(dirname "$0")" && pwd)"
DEST="${APP_DEST:-$HOME/Applications}"
APP="$DEST/PDF to Sheet.app"
mkdir -p "$DEST"
BUILD="$(mktemp -d)"

[ -d "$PROJECT/.venv" ] || { python3 -m venv "$PROJECT/.venv" && "$PROJECT/.venv/bin/pip" install -q -r "$PROJECT/requirements.txt"; }

# --- icon: render an SVG to PNGs with PyMuPDF, then build an .icns ---
cat > "$BUILD/icon.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <rect x="64" y="64" width="896" height="896" rx="200" fill="#2563eb"/>
  <path d="M300 200h300l144 144v400a40 40 0 0 1-40 40H300a40 40 0 0 1-40-40V240a40 40 0 0 1 40-40z" fill="#fff"/>
  <path d="M600 200v110a34 34 0 0 0 34 34h110z" fill="#bfd3fb"/>
  <g fill="#2563eb"><rect x="330" y="470" width="150" height="26" rx="6"/><rect x="330" y="530" width="150" height="26" rx="6"/><rect x="330" y="590" width="150" height="26" rx="6"/>
  <rect x="330" y="650" width="150" height="26" rx="6"/></g>
  <g fill="#16a34a"><rect x="500" y="470" width="190" height="26" rx="6" opacity=".35"/><rect x="500" y="530" width="190" height="26" rx="6" opacity=".35"/><rect x="500" y="590" width="190" height="26" rx="6" opacity=".35"/><rect x="500" y="650" width="190" height="26" rx="6" opacity=".35"/></g>
</svg>
SVG
mkdir "$BUILD/icon.iconset"
"$PROJECT/.venv/bin/python" -W ignore - "$BUILD" <<'PY'
import sys, pymupdf
b = sys.argv[1]
svg = pymupdf.open(f"{b}/icon.svg")
pdf = pymupdf.open("pdf", svg.convert_to_pdf())
for size in (16, 32, 64, 128, 256, 512, 1024):
    pix = pdf[0].get_pixmap(matrix=pymupdf.Matrix(size / 1024, size / 1024), alpha=True)
    pix.save(f"{b}/s{size}.png")
PY
for s in 16 32 128 256 512; do
  cp "$BUILD/s$s.png" "$BUILD/icon.iconset/icon_${s}x${s}.png"
  cp "$BUILD/s$((s*2)).png" "$BUILD/icon.iconset/icon_${s}x${s}@2x.png"
done
iconutil -c icns "$BUILD/icon.iconset" -o "$BUILD/AppIcon.icns"

# --- bundle ---
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BUILD/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>PDF to Sheet</string>
  <key>CFBundleDisplayName</key><string>PDF to Sheet</string>
  <key>CFBundleIdentifier</key><string>local.pdf-to-sheet</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/zsh
PROJECT="$PROJECT"
URL="http://127.0.0.1:5757"
mkdir -p "\$HOME/.pdf-to-sheet"
# Already running (e.g. second click): just bring up the page.
if curl -s -o /dev/null --max-time 1 "\$URL"; then open "\$URL"; exit 0; fi
cd "\$PROJECT" || exit 1
# On Apple Silicon always run natively: the dependencies were installed for the native architecture.
ARCH=()
[[ "\$(sysctl -in hw.optional.arm64 2>/dev/null)" == "1" ]] && ARCH=(arch -arm64)
# exec so quitting the Dock icon stops the server too.
exec "\${ARCH[@]}" "\$PROJECT/.venv/bin/python" -W ignore app.py >> "\$HOME/.pdf-to-sheet/app.log" 2>&1
LAUNCH
chmod +x "$APP/Contents/MacOS/launch"
rm -rf "$BUILD"
echo "Built: $APP"
