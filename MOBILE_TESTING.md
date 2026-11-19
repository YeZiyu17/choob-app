# Choob Mobile: final branch

The team's **`final` branch** combines the latest `choob-rehearsal` baseline with
the Mobile work first tested on local branch `mobile/pwa-local-test`. The earlier
`main` and `choob-rehearsal` branches remain available. Future feature branches
should start from and merge into `final`; see [the team guide](TEAM_GUIDE.md).

Mobile changes add install metadata, app icons, and phone display support. They
do not change restaurant, address, rating, note, or matching data. Coordinate
shared `index.html` changes and merge one reviewed PR at a time. Uploading code
to GitHub does not start a shared Flask service or deploy the app.

## Start on this computer

Use the same Python environment and dependencies described in `TEAM_GUIDE.md`.
Port **7872** keeps this preview separate from the rehearsal app and its browser
storage.

```bash
python start_choob.py --local --port 7872
```

Open <http://127.0.0.1:7872/>. Keep using this exact address so your test records
stay in the same browser storage. The local mode uses the bundled Philadelphia data;
free-text Discover still needs the separately configured local chat model. For
Gemini + Tavily, omit `--local` and enter your own API keys at the hidden prompts.
Keep keys on the server, out of source files and screenshots.

### Gemini + Tavily on a phone

On macOS, after downloading the project, run
`chmod +x "Start Mobile Online.command"` once in the project folder, then
double-click **Start Mobile Online.command** in Finder. Web uploads and ZIP
downloads may not preserve the executable permission. The launcher
asks for Gemini and Tavily keys using hidden terminal input, then starts the
online Discover provider on **7873**, accessible over Wi-Fi. It does not upload
code, create a public tunnel, or write keys to a file. The current local-only
preview on 7872 may stay running separately.

Use `http://<computer-Wi-Fi-IP>:7873/` on the phone. Open Discover and confirm it
shows the online-menu mode and city choices. A running service with valid keys
is required before online requests can succeed. Preferences and menu-search
requests are sent to Gemini/Tavily when this mode is used.

Add this **7873** address to the phone's Home Screen if you want the online
version. Each host/port and installed app can have separate browser storage;
records from 7872 are not automatically transferred. After stopping the server,
the phone cannot call the app until it is started again. The launcher prefers
this project's `.venv`; the existing development computer also supports its
older sibling Python environment.

## Desktop checks

1. Open the page in a current Chrome or Edge browser on this computer.
2. Check the app manifest in browser developer tools. Confirm the Choob name,
   start page, standalone display mode, and app icons load successfully.
3. Check available installation controls, install Choob where supported, and
   launch it from the installed icon. Confirm it opens in its own app window.
4. Use phone-size viewports, including a narrow phone and landscape. Check page
   navigation, scrolling, buttons, text inputs, overlays, and the bottom bar.
5. Log a meal manually, open Passport, refresh, and confirm the meal remains.
   Try a photo upload and Discover with the required model/network setup.
6. Refresh after a code change and confirm the current build appears. Check
   browser console and failed network requests.

## Phone browser checks over Wi-Fi

```bash
python start_choob.py --local --port 7872 --lan
```

Connect the phone and computer to the same trusted Wi-Fi. Open
`http://<computer-LAN-IP>:7872/` on the phone, using the computer's Wi-Fi IP from
its network settings. `0.0.0.0` and the phone's `localhost` are not that address.
The computer must remain awake with the server running. Network isolation or a
firewall may prevent a connection. Stop the server with `Ctrl+C` when finished.

Plain LAN HTTP is useful for browser layout and navigation checks. It does not
meet the HTTPS requirement for full PWA/service-worker testing on the phone.
The localhost exception applies to the device running the server. Use a trusted
HTTPS address for the complete phone installation check; this local task does
not deploy the app or create a public tunnel.

## Real-device installation checklist

Use the final app's trusted HTTPS address, and record the phone OS/browser.

- **iPhone / Safari:** open the page, use Share → Add to Home Screen, and enable
  Open as Web App when that option is available. Check the icon, app name, and
  launch behavior.
- **Android / Chrome:** use Install app or Add to Home screen when offered.
  Launch from the resulting icon and check the standalone window.
- In the installed app, test photo selection, meal logging, Passport/map,
  Discover, Connect, external map links, refresh, and returning from another app.
- Check screen edges, portrait/landscape, long content, the on-screen keyboard,
  dialogs, and bottom navigation. Test teammates' new fields after integration.
- Confirm saved meals remain in the installed app after closing and reopening.
  Browser storage may be separate from the ordinary browser or another URL;
  do not assume existing rehearsal records are copied automatically.

PWA installation does not move Flask, CLIP, or the recommendation service onto
the phone. AI features still need the running backend, models, and the network
connections required by the selected provider.

## Verification record

Local verification on **November 18, 2026**, at `http://127.0.0.1:7872/`:

- **104 Python tests passed:** the existing 99 regression checks plus five PWA
  delivery/worker checks. The worker checks execute its lifecycle and request
  handling in Node, including bypassing API/mutation requests and preserving
  unrelated caches. No model downloads or external API keys were needed.
- **Browser layout passed:** Chromium at 320×568, 375×667, 390×844, 430×932,
  480×900 and touch landscape 844×390. All five main screens kept navigation
  visible with no horizontal overflow. The original desktop preview frame
  remained in place at 1440×1000.
- **PWA configuration passed:** Chrome parsed the manifest without errors;
  the root-scoped worker became active. A disposable non-incognito Chrome
  profile reported **zero installability errors**.
- **Real browser interactions passed:** install-help dialog and Escape/focus
  handling; a manually entered two-dish meal saved to Passport and survived a
  refresh; inputs stayed at 16px; backend status and invalid-image responses
  remained correct; no uncaught page errors were observed.
- **Offline recovery passed:** only `/offline.html` appeared in Cache Storage.
  Browser offline mode showed the explanation; reconnecting and pressing
  **Try again** returned to the live app. App HTML, photos, scripts and AI
  responses were not saved by the service worker.
- **Platform-specific UI passed in Chromium emulation:** iPhone/Android
  instructions, sample JPEG selection/preview, and landscape dialog sizing.
  This does not establish compatibility with physical Safari or Android.

The detailed screenshots and browser JSON from this run were kept in the
author's local QA folder, outside the published repository. The temporary
automated browser profiles were separate from the user's ordinary browser and
used isolated test storage. No new Python runtime dependency was added.

**Phone follow-up, November 19, 2026:** the user reported that all features were
working on their phone after configuring the online service. The phone model,
OS and browser version were not recorded. This user report is distinct from
the automated Chromium evidence above.

**Still pending:** recorded device/browser details, cross-platform real-device
coverage, full HTTPS PWA/offline verification, and regression testing teammates'
new fields after integration. Viewport/UA emulation is not a real-device test.
The original AI models were not re-evaluated for accuracy in this Mobile change.

## Updating the shared final build

Pull the latest `final` before starting a feature branch and after each merge.
Restart the local server for backend changes and refresh the phone. With the
same URL, the existing Home Screen entry can continue opening the updated app.
Recheck phone layouts whenever Snap, Passport, Discover or Connect changes.
The original rehearsal branch remains available as an earlier version.

References: [PWA installability and HTTPS](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable),
[Safari Home Screen apps](https://support.apple.com/guide/iphone/iphea86e5236/ios).
