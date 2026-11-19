#!/bin/zsh
set -e

# Keep this launcher portable within this checkout; never store API keys here.
CHOOB_MOBILE_DIR="${0:A:h}"
cd -- "$CHOOB_MOBILE_DIR"
export PYTHONDONTWRITEBYTECODE=1
CHOOB_MOBILE_PYTHON="$CHOOB_MOBILE_DIR/.venv/bin/python"
if [[ ! -x "$CHOOB_MOBILE_PYTHON" ]]; then
  # Compatibility fallback for the existing development computer only.
  CHOOB_MOBILE_PYTHON="$CHOOB_MOBILE_DIR/../recommendation-work/venv/bin/python"
fi
if [[ ! -x "$CHOOB_MOBILE_PYTHON" ]]; then
  print 'Choob Python environment was not found. Follow TEAM_GUIDE.md to create .venv first.'
  read '?Press Return to close.'
  exit 1
fi

print 'Choob Mobile: final build with Gemini + Tavily (local Wi-Fi).'
print 'Enter your API keys at the hidden prompts. Nothing is saved to source files.'
print 'Phone address: http://<this-computer-Wi-Fi-IP>:7873/'
print 'Keep this window open while testing. Press Control+C to stop.'
exec "$CHOOB_MOBILE_PYTHON" start_choob.py --lan --port 7873 "$@"
