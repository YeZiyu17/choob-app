"""Start the team rehearsal build on this computer."""
import argparse
import os
import warnings
from getpass import GetPassWarning, getpass


def main():
    parser = argparse.ArgumentParser(description="Start Choob for rehearsal.")
    parser.add_argument("--local", action="store_true", help="Use the bundled Philadelphia data.")
    parser.add_argument("--port", type=int, default=7861, help="Local port (default: 7861).")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")

    if not args.local:
        keys = (
            ("Gemini", "GEMINI_API_KEY", ("GEMINI_API_KEY", "GOOGLE_API_KEY")),
            ("Tavily", "TAVILY_API_KEY", ("TAVILY_API_KEY",)),
        )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                for label, variable, aliases in keys:
                    if any(os.environ.get(name, "").strip() for name in aliases):
                        continue
                    key = getpass(f"{label} API key (input hidden): ").strip()
                    if not key:
                        parser.exit(2, f"A {label} key is required for online Discover.\n")
                    os.environ[variable] = key
        except (EOFError, GetPassWarning):
            parser.exit(2, "Open a terminal with hidden input or set the API keys in the environment.\n")
        except KeyboardInterrupt:
            parser.exit(130, "\nChoob startup canceled.\n")

    os.environ["CHOOB_DISCOVER_PROVIDER"] = "local" if args.local else "gemini_tavily"

    # The app reads the Discover provider during import.
    from app import app

    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
