# Choob Team Collaboration and Local Setup Guide

All five teammates use the same [GitHub repository](https://github.com/YeZiyu17/choob-app) to store and edit the code. We currently **collaborate through GitHub and run the app on our own computers**. No hosting account is required for this workflow.

## Run the App Locally

1. Install **Python 3.11**. On Windows, select **Add Python to PATH** during installation.
2. Open the repository, select the `main` branch, and choose the green **Code → Download ZIP** button. Extract the ZIP to a folder on your computer.
3. Open a terminal in the extracted `choob-app-main` folder. Make sure it contains `app.py` and `requirements.txt`.
4. Run the commands for your operating system below.

macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows (Command Prompt / CMD):

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

Open **http://localhost:7860/** in your browser and keep the terminal running. To stop the server, press `Ctrl+C` in the terminal. To run the app again later, open the same folder, activate `.venv`, and run `python app.py`.

The first image recognition and text recommendation requests download public models from the internet. Stay connected, allow several GB of free disk space, and make sure enough memory is available. The initial download and loading can take some time; close memory-intensive applications if needed. Later runs reuse the models cached on your computer.

Start with **Discover** and enter an English food preference, such as `cheesecake or tiramisu`. Then try uploading a food photo in **Snap**. Recommendations use sampled reviews from 123 restaurants. They do not represent complete or current menus and cannot verify dietary restrictions or allergy requirements.

## Collaborate on the Code

Downloading the ZIP is a convenient way to try the app. For ongoing development, install **GitHub Desktop**, sign in to your GitHub account, and use **File → Clone repository → URL** to clone this repository. Everyone already has collaborator access, so there is no need to create a separate repository or fork.

Follow these steps whenever you make changes:

1. Switch to `main` and choose **Fetch origin / Pull origin** to get the team's latest code.
2. Create your own branch from `main`, such as `person1-ui`, `person2-data`, or `person3-ai`.
3. Edit the files, run and check the app on your computer, then **Commit → Publish branch / Push origin**.
4. Choose **Create Pull Request**, select `main` as the target branch, and describe what changed and how you checked it.
5. Ask another teammate to review the pull request before merging. Everyone else can then update their local `main`.

Keep `.venv`, model caches, passwords, and raw review files that have not been approved for sharing out of GitHub. When updating the recommendation exports, keep the CSV, NPY, and manifest files from the same build together.

## Team Responsibilities

| Team member | Responsibility | Main handoff |
|---|---|---|
| Person 1 | UI Design + User Flow | Maintain `index.html` and coordinate API interfaces with Person 4 |
| Person 2 | Data Processing | Provide cleaned review and restaurant data using the contract in `data/README.md` |
| Person 3 | AI Model + Recommendation | Maintain recognition, recommendations, data exports, and documentation of model limitations |
| Person 4 | App Integration + Deployment | Connect Flask to the UI, support local setup, and arrange cloud deployment if needed |
| Person 5 | Evaluation + Testing | Test new images, evaluate recommendations manually, and check complete user flows |

## What Is Shared?

- **GitHub shares code and version history.** After a teammate's changes are committed and merged, others must update their local code to see them.
- **Each teammate runs the app on their own computer.** `localhost` refers to the computer opening the page. Sending someone your localhost URL will not give them access to your app.
- **Collect saves items only in the current browser.** Saved items do not automatically sync across computers or browsers. There is currently no shared team account or database.
- If everyone later needs to use the full AI app through one shared URL, we can arrange hosting. GitHub repository pages let teammates view the code directly, but GitHub Pages cannot run this project's Flask server and Python models.
