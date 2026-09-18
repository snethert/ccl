#!/bin/sh
# Render the reference screens from screens.html.
# Usage: ./render.sh [scale] [screen numbers...]   (default: scale 3, all 23)
# Output: ../NN-<slug>.png, 1440x900 at the given scale.
set -e
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
SCALE="${1:-3}"; shift 2>/dev/null || true
LIST="$*"; [ -z "$LIST" ] && LIST="$(seq 1 23)"
for n in $LIST; do
  nn=$(printf '%02d' "$n")
  slug=$(grep -o "id=\"f$nn\"><div class=\"cap\"><b>$n</b>[^<]*" screens.html | sed -e 's/.*<\/b>//' -e 's/ —.*//' | tr 'A-Z' 'a-z' | sed -e 's/[^a-z0-9]\{1,\}/-/g' -e 's/^-//' -e 's/-$//')
  out="../$nn-$slug.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 \
    --force-device-scale-factor="$SCALE" --virtual-time-budget=3000 \
    --screenshot="$out" "file://$PWD/screens.html?screen=$n" >/dev/null 2>&1
  echo "$out"
done
