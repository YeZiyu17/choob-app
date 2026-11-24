# Choob Team Collaboration and Local Setup Guide

The [Choob repository](https://github.com/YeZiyu17/choob-app) opens on the `final` branch. Follow the steps below to run the app on your own computer.

## Run the Final Build

1. Install **Python 3.12**. The verified setup used macOS ARM64 and Python 3.12.14; the Windows commands are not a claim of Windows testing. On Windows, select **Add Python to PATH** during installation.
2. From the repository homepage, choose **Code → Download ZIP** and extract it. Open Terminal (macOS) or Command Prompt (Windows) in the extracted folder that contains `start_choob.py` and `requirements.txt`.
3. Create and activate the virtual environment for your operating system.

   **macOS (Terminal)**

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows (Command Prompt)**

   ```bat
   py -3.12 -m venv .venv
   .venv\Scripts\activate.bat
   ```

4. Install with `python -m pip install -r requirements.txt`. For the recorded **macOS ARM64 / Python 3.12** package set, use `python -m pip install -r requirements-macos-arm64-py312-verified.txt` instead, then run `python -m pip check`. The older Intel/Python 3.11 profile remains unverified by this audit.
5. Choose one startup command in the same terminal.

   - **Start without API keys** with `python start_choob.py --local`. You can scan a photo, log it in Passport and use the preset choices in Discover with the bundled Philadelphia data.
   - **Run Discover with live menus** with `python start_choob.py`. Enter your own [Gemini key](https://aistudio.google.com/app/apikey) and [Tavily key](https://app.tavily.com/home) when prompted. Input is hidden.

6. Keep the terminal running and open [http://127.0.0.1:7861/](http://127.0.0.1:7861/) in a browser on the same computer. Use the [checklist below](#final-checklist) to try Snap and Discover. Keep an internet connection for public model downloads and metadata lookup. The recorded clean-environment check reused public model assets and did not test a first download.

Press `Ctrl+C` in the terminal to stop Choob. For later sessions, activate the same virtual environment and run your chosen startup command again. If port 7861 is busy, add `--port 7863` to that command and open the address printed in the terminal.

## Test on a phone

After installing the dependencies, run `python start_choob.py --lan --port 7873`.
On macOS you can instead run `chmod +x "Start Mobile Online.command"` once after
downloading, then double-click **Start Mobile Online.command**. Enter your
own Gemini and Tavily keys at the hidden prompts. Keep the computer and terminal
running, connect the phone to the same Wi-Fi, and open
`http://<computer-Wi-Fi-IP>:7873/`. The phone's `localhost` is not the computer.

See [Mobile instructions and recorded tests](MOBILE_TESTING.md) for Home Screen
steps and HTTPS requirements. An updated final build appears after updating the
computer's code, restarting the service when needed, and refreshing the phone.
Keep the same host/port to retain the same browser storage.

## Final documentation handoff

Submit the English technical report separately through the course's designated channel. Use the [submission verification and resources](docs/SUBMISSION.md) and the recorded [final evaluations](README.md#final-documentation-submission) alongside it. A documented, verified local setup is the chosen working-application submission route; no hosted URL is claimed. The raw private Yelp inputs are not needed to run the supplied app exports, but are needed to reproduce the annotation rebuild.

## Final checklist

- **Snap**: Start with the [sample photos](examples/snap/README.md), then try a new photo. Review or correct the dish suggestions and log them as one meal.
- **Discover (live menus)**: Select a city and area and try a request such as `spicy Chinese food`. Check a menu source and its reason, then try **Show more dishes** and save one dish.
- **Passport**: Open **Saved dishes**, use **I tried this**, and confirm the meal in Snap. If you add a location, open its stamp in Passport. Refresh on the same local URL to check that the meal persists.
- **Connect**: Create your profile. In Snap, log a meal at **Kaze Sushi Bar** with an address in Philadelphia, rate the sushi **5★**, and add a second dish rated **2★**. In Connect, check that Amelia's reason mentions the restaurant and the 5★ rating, and that the 2★ dish is listed as not used for matching. Open **Amelia’s map** to see her stamps, tap **Plan a meal together** and check that Discover opens with a request for Philadelphia. Follow a match, refresh, and check the **Following** and **Followers** tabs.

## Collaborate on the Code

Download the ZIP to try the app. To contribute code, clone the repository in GitHub Desktop and accept the repository invitation if it's still pending.

Follow these steps whenever you make changes:

1. Switch to **`final`** and choose **Fetch origin / Pull origin**.
2. Create a feature branch for your change.
3. Edit and test your part, then **Commit → Publish branch / Push origin**. If you edit `index.html`, keep the changes in your screen and coordinate any shared navigation or saved-data changes.
4. Open a pull request with **base branch `final`**. Include a short note on what changed and how you tested it.
5. Pick one teammate to review and merge one PR at a time. After each merge, pull the updated `final` and run the flow that changed, including on a phone when relevant. Before the final presentation, do a full run on the computer you'll present from.

Keep API keys, `.venv`, model caches, and raw review files out of GitHub. Keep the recommendation CSV, NPY, and manifest together if updating those exports.

## What Is Shared?

- **GitHub shares code and version history.** Pull `final` after a merge to get this round's integrated build. The `rehearsal` branch preserves the classroom rehearsal and `archive` holds the earlier project history. A teammate's separate branch does not enter the shared build until merged into `final`.
- **Each teammate runs the app on their own computer.** `localhost` refers to the computer opening the page. Sending someone your localhost URL will not give them access to your app.
- **Passport and Saved dishes use the current browser's storage.** Use the same browser/app and the same address and port to see the same records. Computer and phone records are not automatically synchronized.
- If everyone later needs to use the full AI app through one shared URL, we can arrange hosting. GitHub repository pages let teammates view the code directly, but GitHub Pages cannot run this project's Flask server and Python models.
