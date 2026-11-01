# Person 4 browser verification — 1 Nov 2026

Environment: Intel Mac x86_64, Python 3.11.9 compatibility environment, Flask on `http://127.0.0.1:7861`, ChatGPT in-app browser. This is a local browser test, not a public deployment test.

## Browser-observed flows

1. Snap accepted photo:
   - Uploaded newly selected Wikimedia `Pizza.jpeg`.
   - Live CLIP response shown as `Pizza`, relative score 99.5%, confirmation required.
   - Confirmed unchanged and saved.
   - Collect showed `Saved in this browser · 1 dish` and source `Live Snap inference`.
2. Persistence and duplicate handling:
   - Reloaded the page, reopened Collect, and still saw one saved Pizza.
   - Repeated the same Snap save. Count remained one and toast showed `Already in your collection`.
3. Snap uncertain/manual correction:
   - Uploaded newly selected Wikimedia `Sushi!.jpg`.
   - Live CLIP response shown as `Uncertain / unsupported dish`; suggested candidate `Sushi`.
   - Entered `Sushi` manually and saved. Collect displayed source `Snap · manual dish name` and kept Unknown cuisine/category rather than inventing metadata.
4. Discover live inference:
   - `I want sushi with fresh fish.` returned Sushi, Sushi, Lunch Sushi Special, Sushi, Sushi Boat.
   - Saved the first result; second click showed `Already saved`.
   - `I want a sweet dessert, such as tiramisu or cheesecake.` returned Tiramisu Dessert, Cheesecake, Sweet Potato Cheesecake, Cheesecakes, Baklava Cheesecake.
   - The two Top-5 lists were different.
5. Consecutive-request protection:
   - Started a sushi request and immediately started the dessert request.
   - Final rendered list was the dessert list (`Tiramisu Dessert` first), confirming the older response did not overwrite the latest request.
6. Results page:
   - Displayed current export `Oct 29, 2026 · 5a7c04c0a5f0`.
   - Displayed 3,526 processed reviews, 8,667 dish mentions and 5,993 restaurant–dish pairs.
   - Displayed `Human recommendation relevance evaluation is still pending for this build.`
   - Recorded evaluation content remained explicitly labelled `RECORDED`.

The browser checks prove the local UI flow and persistence behavior. They are separate from the 61 automated checks, the direct model benchmark and the loopback HTTP checks.
