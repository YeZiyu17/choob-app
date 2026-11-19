# Choob Rehearsal Setup and Team Guide

Instructors, evaluators, and teammates can use this guide to run the **choob-rehearsal** version. The [GitHub repository](https://github.com/YeZiyu17/choob-app/tree/choob-rehearsal) is public, so no invitation or GitHub account is required to read the code or download it. The app runs on your own computer; opening GitHub alone does not launch it.

## Run the Rehearsal Build

### 1. Get the rehearsal code

Open the [choob-rehearsal branch](https://github.com/YeZiyu17/choob-app/tree/choob-rehearsal), confirm that the branch selector says **choob-rehearsal**, and choose **Code > Download ZIP**. Extract the ZIP before running anything. Open a terminal in the extracted folder containing `app.py`, `start_choob.py`, and `requirements.txt`. Keep the `data/` and `static/` folders with these files.

### 2. Install Python and dependencies

Install **Python 3.11**. On Windows, select **Add Python to PATH** during installation. Internet access is required for installation and the initial model downloads; allow time for the machine-learning dependencies to install.

**macOS:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Windows (Command Prompt / CMD):** These activation commands are for CMD, not PowerShell.

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

**Intel Mac:** In the activated Python 3.11 environment, replace the installation command above with:

```bash
python -m pip install -r requirements-intel-py311.txt
```

This compatibility profile uses PyTorch 2.2.2 and keeps NumPy below 2. Use it when creating the environment rather than installing both profiles.

### 3. Choose online Discover or local practice

**Option A: Online menus with Gemini + Tavily**

Create your own [Gemini key](https://aistudio.google.com/app/apikey) and [Tavily key](https://app.tavily.com/home). Both services must accept requests from your account. In the activated environment, run:

```bash
python start_choob.py
```

Paste the Gemini key and then the Tavily key at the terminal prompts. Input is hidden: characters are not displayed while you type or paste. Press Enter after each key. The launcher also reuses keys already set in its environment (`GEMINI_API_KEY` or `GOOGLE_API_KEY`, and `TAVILY_API_KEY`). Keys are not bundled in GitHub. Online Discover sends dining preferences to these services and retrieves public menu sources.

**Option B: Practice without API keys**

```bash
python start_choob.py --local
```

This skips both key prompts. In Discover, use the cuisine and flavor **choice buttons** to explore the bundled Philadelphia recommendations. Local free-text chat needs a separate MLX/Qwen environment and model outside this repository; it is not set up by `requirements.txt`. Without that extra setup, the app reports that free-text AI is unavailable and still provides the choice buttons. Snap, meal logging, Passport, and the Connect demo can also be explored locally.

Neither option includes model weights in the ZIP. The first image recognition request downloads **CLIP**, and the first local recommendation request may download **MiniLM**. Keep internet access available for those initial downloads. Map tiles also require internet access. `--local` does not mean a fresh installation is fully offline.

### 4. Open the app and try the flow

After the terminal reports that the server is running, open **http://127.0.0.1:7861/** in a browser **on the same computer**. Keep the terminal running. Start with the [rehearsal checklist](#rehearsal-checklist) below: Snap, Passport, Discover, then Connect. A GitHub page or a standalone `index.html` does not run the Python AI endpoints.

For later runs, open a terminal in the same folder, activate `.venv` with the command for your operating system, and run your chosen launch command again. Stop the server by pressing `Ctrl+C` in its terminal.

### Troubleshooting

| What you see | What to check |
| --- | --- |
| `python3.11` or `py -3.11` is not found | Install Python 3.11, then reopen the terminal. On Windows, check the Python launcher and PATH installation options. |
| A module such as `flask` is missing | Activate this folder's `.venv` and run the dependency installation command for your machine. |
| Gemini or Tavily rejects a request | Check that both keys are valid and that the corresponding accounts allow API requests. Restart the launcher with the correct keys. Use `--local` for practice without keys. |
| Port 7861 is already in use | Run `python start_choob.py --port 7863`, or `python start_choob.py --local --port 7863`, then open `http://127.0.0.1:7863/`. |
| The first scan or local recommendations take time | Allow the initial model download to finish and check the terminal for a download or connection error. Later requests reuse cached weights. |
| Local free-text chat is unavailable | Use the cuisine/flavor buttons, or restart in Gemini + Tavily mode with valid keys. The optional MLX/Qwen setup is not included. |
| The page cannot connect | Confirm that the server is still running and use the exact address and port it prints. `localhost` refers to the computer opening the browser. |
| Previous meals or saved dishes are missing | Use the same browser, hostname, and port as before. These records use browser storage rather than a shared account. |


## Rehearsal checklist

- **Snap**: Start with the [sample photos](examples/snap/README.md), then try a new photo. Review or correct the dish suggestions and log them as one meal.
- **Discover**: Select a city and try a request such as `spicy Chinese food`. Check a menu source and its reason, then try **Show more dishes** and save one dish.
- **Passport**: Open **Saved dishes**, use **I tried this**, and confirm the meal in Snap. If you add a location, open its stamp in Passport. Refresh on the same local URL to check that the meal persists.
- **Connect**: Create your profile (name + avatar). With no meals logged, check that demo passports still show. Log a meal with several dishes (for example gyoza and a tuna roll, placed in Philadelphia), then check that each match shows a reason, shared tags, their notes on dishes you share, and **Save to try** with the restaurant. Follow a match, refresh, and check the **Following** and **Followers** tabs and counts. A saved dish should show "<name>’s pick" in Saved dishes.

## Collaborate on the Code

Download the ZIP to try the app. To contribute code, clone the repository in GitHub Desktop and accept the repository invitation if it's still pending.

Follow these steps whenever you make changes:

1. Switch to `choob-rehearsal` and choose **Fetch origin / Pull origin**.
2. Create a branch for your feature, such as `rehearsal-snap`, `rehearsal-passport`, `rehearsal-discover`, or `rehearsal-connect`.
3. Edit and test your part, then **Commit → Publish branch / Push origin**. If you edit `index.html`, keep the changes in your screen and coordinate any shared navigation or saved-data changes.
4. Open a pull request into `choob-rehearsal`. Include a short note on what changed and how you tested it.
5. Pick one teammate to review and merge one PR at a time. After each merge, pull the updated rehearsal branch and run the flow that changed. Before rehearsal, do a full run on the computer you'll present from.

Keep API keys, `.venv`, model caches, and raw review files out of GitHub. Keep the recommendation CSV, NPY, and manifest together if updating those exports.

## What Is Shared?

- **GitHub shares code and version history.** Pull `choob-rehearsal` after a merge to get the latest rehearsal build. The earlier build is on `archive-main`.
- **Each teammate runs the app on their own computer.** `localhost` refers to the computer opening the page. Sending someone your localhost URL will not give them access to your app.
- **Passport and Saved dishes use the current browser's storage.** Run the rehearsal in the same browser and at the same local address and port to see the same records.
- If everyone later needs to use the full AI app through one shared URL, we can arrange hosting. GitHub repository pages let teammates view the code directly, but GitHub Pages cannot run this project's Flask server and Python models.
