# Choob Team Collaboration and Local Setup Guide

All five teammates use the same [GitHub repository](https://github.com/YeZiyu17/choob-app) to store and edit the code. We currently **collaborate through GitHub and run the app on our own computers**. No hosting account is required for this workflow.

## Run the Final Build

1. Install **Python 3.11**. On Windows, select **Add Python to PATH** during installation.
2. Open the repository, select the **`final`** branch, and choose **Code → Download ZIP**. Extract the ZIP to a folder on your computer. Keep any old rehearsal folder separate.
3. Open a terminal in the extracted folder. Make sure it contains `app.py` and `requirements.txt`.
4. Run the commands for your operating system below.

macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python start_choob.py
```

Windows (Command Prompt / CMD):

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python start_choob.py
```

Paste your own [Gemini key](https://aistudio.google.com/app/apikey) and [Tavily key](https://app.tavily.com/home) when prompted. The input is hidden. Open **http://127.0.0.1:7861/** and go to **Discover** to see the city menu. Keep the terminal running and press `Ctrl+C` there when you want to stop the app.

For an Intel Mac with Python 3.11, use `python -m pip install -r requirements-intel-py311.txt` instead of the generic requirements command above.

For later runs, activate `.venv` and run `python start_choob.py` again. If port 7861 is busy, run `python start_choob.py --port 7863` and open the address printed by the server. To practice with the bundled Philadelphia data, run `python start_choob.py --local`.

The first image recognition request downloads CLIP model weights. Stay connected and allow time and disk space for that first request. Later runs reuse the cached weights.

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

## Final checklist

- **Snap**: Start with the [sample photos](examples/snap/README.md), then try a new photo. Review or correct the dish suggestions and log them as one meal.
- **Discover**: Select a city and try a request such as `spicy Chinese food`. Check a menu source and its reason, then try **Show more dishes** and save one dish.
- **Passport**: Open **Saved dishes**, use **I tried this**, and confirm the meal in Snap. If you add a location, open its stamp in Passport. Refresh on the same local URL to check that the meal persists.
- **Connect**: Create your profile (name + avatar). With no meals logged, check that demo passports still show. Log a meal with several dishes (for example gyoza and a tuna roll, placed in Philadelphia), then check that each match shows a reason, shared tags, their notes on dishes you share, and **Save to try** with the restaurant. Follow a match, refresh, and check the **Following** and **Followers** tabs and counts. A saved dish should show "<name>’s pick" in Saved dishes.

## Collaborate on the Code

Download the ZIP to try the app. To contribute code, clone the repository in GitHub Desktop and accept the repository invitation if it's still pending.

Follow these steps whenever you make changes:

1. Switch to **`final`** and choose **Fetch origin / Pull origin**.
2. Create a branch for your feature, such as `final-snap`, `final-passport`, `final-discover`, `final-connect`, or `final-mobile`.
3. Edit and test your part, then **Commit → Publish branch / Push origin**. If you edit `index.html`, keep the changes in your screen and coordinate any shared navigation or saved-data changes.
4. Open a pull request with **base branch `final`**. Include a short note on what changed and how you tested it.
5. Pick one teammate to review and merge one PR at a time. After each merge, pull the updated `final` and run the flow that changed, including on a phone when relevant. Before the final presentation, do a full run on the computer you'll present from.

Keep API keys, `.venv`, model caches, and raw review files out of GitHub. Keep the recommendation CSV, NPY, and manifest together if updating those exports.

## What Is Shared?

- **GitHub shares code and version history.** Pull `final` after a merge to get this round's integrated build. The earlier `main` and `choob-rehearsal` branches are preserved. A teammate's separate branch does not enter the shared build until merged into `final`.
- **Each teammate runs the app on their own computer.** `localhost` refers to the computer opening the page. Sending someone your localhost URL will not give them access to your app.
- **Passport and Saved dishes use the current browser's storage.** Use the same browser/app and the same address and port to see the same records. Computer and phone records are not automatically synchronized.
- If everyone later needs to use the full AI app through one shared URL, we can arrange hosting. GitHub repository pages let teammates view the code directly, but GitHub Pages cannot run this project's Flask server and Python models.
