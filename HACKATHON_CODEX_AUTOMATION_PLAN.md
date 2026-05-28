# Doomsday Rapid Agent - OpenAI x Outskill Hackathon Upgrade Plan

## What the judges are asking for

From the kickoff transcript and deck, the strongest signals are:

- Build a real, demo-ready product in the 7-day sprint.
- Optimize for a painful workflow, not a cool AI toy.
- Show automation: agents should do routine work before the human arrives.
- Use Codex meaningfully, not just as a badge.
- Make the demo clear enough for a user or investor to understand quickly.

Scorecard from the deck:

| Lens | Points | What Doomsday should prove |
| --- | ---: | --- |
| Technical execution | 25 | The app runs, data flows, models compute, outputs are traceable. |
| Usefulness | 25 | It compresses analyst crisis monitoring and stress modeling from hours to minutes. |
| Creativity and originality | 20 | It is not "chat with stocks"; it is an autonomous risk war-room. |
| Codex usage | 20 | Codex is visibly integrated into the builder workflow and product automation story. |
| Presentation clarity | 10 | Demo tells one tight story: trigger, debate, model impact, human decision. |

## Product thesis

Current pitch:

> Instantly stress-test stocks against real-world crises using AI analysts that debate worst cases and translate those arguments into financial model downside.

Hackathon-grade pitch:

> Doomsday is an autonomous crisis analyst desk. It monitors global shock signals, wakes up when a portfolio exposure is threatened, runs an adversarial analyst tribunal, patches the valuation model with scenario-specific assumptions, and produces an investment committee memo with human approval gates.

## Highest-impact upgrade ideas

### 1. Autonomous Crisis Watchtower

Build a scheduled monitor that checks a watchlist and only triggers a full Doomsday run when a material risk changes.

Inputs:

- Ticker watchlist.
- Crisis sources: Tavily/live news, Elastic macro risk DB, market signals from yfinance.
- Trigger rules: VIX spike, oil shock, ticker drawdown, risk keyword match, sector-specific geopolitical event.

Outputs:

- "No action" when nothing material changed.
- "Human review required" when a risk crosses threshold.
- Stored incident snapshot for the app.

Why it wins:

- Directly matches the kickoff language: scheduled work, connectors, agents acting when the human is not there.
- Turns the app from a dashboard into a workflow.

Suggested implementation:

- Add `automation_watchtower.py`.
- Store incidents in `data/incidents.json`.
- Add a Streamlit tab/section: "Autonomous Watchtower".
- Add a local command demo: `python automation_watchtower.py --watchlist NVDA,TSM,RELIANCE.NS --chaos 0.7`.

### 2. Codex Model Patch Generator

Let the user ask: "This shock affects semiconductors through export controls. Update the stress math." The app generates a proposed model patch or scenario config, then asks the human to approve before applying.

Honest Codex framing:

- Inside this repo, Codex is the builder/operator that creates, reviews, and patches scenario logic.
- In the app, the product exposes a "Codex handoff" artifact: a precise engineering task, model assumptions, expected tests, and generated diff instructions.
- If an API key is available, an OpenAI coding model can generate a patch proposal through the Responses API; otherwise the app still produces a high-quality task packet for Codex.

Outputs:

- `codex_task.md`: the task brief.
- `scenario_patch.json`: assumptions to apply.
- Optional generated code patch proposal.

Why it wins:

- It makes Codex usage concrete: model improvement is not hidden in the build process; it becomes part of the product loop.
- It shows human-in-review for critical changes.

### 3. Investment Committee Memo Autopilot

After the tribunal and valuation run, generate a one-page memo:

- Executive verdict.
- Top three risks.
- Bear, bull, judge summaries.
- Valuation delta and key assumptions.
- "Approve hedge", "Escalate", or "Dismiss" recommendation.
- Audit trail links: data sources, debate transcript, telemetry.

Why it wins:

- Converts analysis into an action artifact.
- Great for demo clarity and usefulness.

Suggested implementation:

- Add `reporting.py` with Markdown generation.
- Add download button in Streamlit.
- Optional PDF later, but Markdown is faster and safer for the hackathon.

### 4. Risk Memory and Regression Bench

Every analysis becomes a saved case. Codex can then run regression checks after code changes:

- Same ticker and chaos settings.
- Same or similar top risks expected.
- Valuation output must remain within tolerance unless the model changed intentionally.

Why it wins:

- Shows production thinking.
- Helps technical execution score.
- Lets you say: "Codex did not just write code; it continuously tested whether the analyst desk stayed sane."

Suggested implementation:

- Add `cases/` with 3 golden scenarios: `NVDA`, `TSM`, `JPM`.
- Add `test_regression_cases.py`.

### 5. Live Human Review Gate

Before applying the harshest valuation assumptions, show a review panel:

- Trigger risk.
- Proposed revenue haircut.
- Proposed margin compression.
- Proposed WACC premium.
- Buttons: approve, soften, reject.

Why it wins:

- Mirrors the kickoff call: humans only where judgment is critical.
- Makes the agentic UX distinctive.

## Recommended build order

1. Add Investment Committee Memo Autopilot.
2. Add Watchtower incident store and Streamlit section.
3. Add Codex task/patch packet generator.
4. Add 2-3 regression cases.
5. Polish demo script and submit.

This order maximizes visible impact while keeping the engineering risk controlled.

## Demo story

1. "A portfolio manager tracks NVDA and TSM. They do not have time to read every war, export-control, and supply chain headline."
2. Run the Watchtower. It detects a semiconductor exposure trigger.
3. Open the app incident. Launch the Doomsday tribunal.
4. Bear, bull, and judge debate the risk with evidence.
5. The valuation engine translates the debate into downside.
6. The app generates an IC memo.
7. Show the Codex handoff packet: "Here is how the system asks Codex to add a new export-control stress module, with tests and human approval."

## Submission positioning

One-line:

> Doomsday replaces the slow analyst spreadsheet with an autonomous crisis desk for public equities.

What changed during this hackathon:

- Added continuous monitoring instead of one-off analysis.
- Added workflow automation and human review gates.
- Added Codex task generation for model evolution.
- Added investor-ready action artifacts.

What to avoid saying:

- Do not claim it predicts crashes.
- Do not claim fully autonomous trading.
- Do not claim Codex is embedded as a live production agent unless a real API/tool path is implemented.

Best framing:

> It is a stress-testing and decision-support system. It automates the repetitive research and modeling steps, then escalates high-stakes assumptions to the human.
