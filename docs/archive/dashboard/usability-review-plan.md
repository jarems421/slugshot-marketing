# Dashboard usability and design pass: preparation

This is the brief for the final usability and design pass. It changes presentation only. Metric rules (`dashboard/views.py`), policy gates and the research feature freeze stay as they are.

## Scope

Seven pages and their drawers: Overview, Content, Research, Game, Experiments, Publish and Settings.

## Method

1. **Task walkthroughs, with the owner driving and Claude watching.** Time each task and note where the owner hesitates. These are the tasks the owner will actually repeat:
   - "Is anything stale or broken?" (status line → Settings)
   - "How did yesterday's EN Short do on each platform?" (Content → upload drawer)
   - "Register a new render and send it to YouTube EN and TikTok EN" (Content → Publish → approve)
   - "Mark a TikTok inbox draft as posted"
   - "What does the research say about curiosity hooks?" (Research → Knowledge search)
   - "Is the opener experiment ready to read?" (Experiments)
   - "Export a snapshot for ChatGPT" (Settings → Export)
2. **Screenshots** with `tests/dashboard_screens.py`, in dark and light, at 1440 and 600 px, on fixture data (`ss dash demo`) and on live data once accounts are connected.
3. **Accessibility checks:**
   - keyboard only: tab order, Enter on table rows, Escape closes drawers;
   - visible focus;
   - contrast in both themes;
   - 200% zoom;
   - reduced motion;
   - screen-reader names for the icon buttons.
4. **One change list.** Each item gets a recommendation level (A/B/C/D/S) and an owner decision before anything is changed.

## Issues already seen (2026-11-25)

| Where | Issue | Candidate fix |
|---|---|---|
| Publish, queue | Experiment and route cells wrap onto 2–3 lines at 1440 px | shorter route labels; experiment as a chip; hide columns under 900 px |
| Publish, drawer | Long drawer: the approve box sits below the fold on laptop screens | sticky footer for Save, Approve and Delete |
| Publish, accounts vs Settings → connections | Two places to connect the same account | one connection row per account with both "analytics" and "uploads" states; Publish links to it |
| Publish, preview | Headless screenshots show a black frame (real browsers show frame 0.5 s) | none needed; check on the owner's machine |
| Status line | Wording fixed ("1 source needs attention") | done |
| Overview, Game | Empty states dominate until accounts are connected | revisit with live data; nothing to change before then |
| Nav | 7 pages plus Settings; Publish and Content overlap (versions vs posts) | consider "Content" with tabs Published, Concepts, Renders, Publish queue |
| Research | Many panels; the knowledge browser is the useful part day to day | order panels by use; collapse the rarely used ones |

## Not in scope

New metrics, scores or rankings; adding numbers across platforms; new pages for research tooling; hosting; logins; scheduled posting.

## Done when

- every task above completes without help;
- no horizontal scroll at 600 px;
- keyboard and contrast checks pass in both themes;
- `ss smoke --dashboard` passes;
- before/after screenshots are saved in `out/dashboard_screens_final/`.
