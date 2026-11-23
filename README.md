# Agent-readiness research for 100 apps

An agent researches 100 apps from their vendors' own docs: auth method, self-serve vs gated, API
surface, existing MCP, and whether an agent toolkit could be built today. Separate checks then try
to catch its mistakes. The case study page is `docs/index.html`; all data is in `docs/results.json`.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r agent/requirements.txt
Copy-Item .env.example .env        # then fill in the three keys
.\.venv\Scripts\python.exe agent/connectTavily.py            # one-time: registers your Tavily key with Composio
.\.venv\Scripts\python.exe agent/runResearch.py --app Stripe --passName demo   # one app end to end
.\.venv\Scripts\python.exe agent/runResearch.py --all --passName pass1         # all 100, resumable
```

Keys needed in `.env`: `COMPOSIO_API_KEY`, `GEMINI_API_KEY` (free tier works), `TAVILY_API_KEY`
(free tier works).

## Pipeline

| Step | File | Uses a model? |
|---|---|---|
| Research agent (search + read docs, fill schema with a quote per field) | `agent/researchAgent.py` | yes |
| Evidence check: is each quote really on the cited page | `agent/evidenceChecker.py` | no |
| Composio catalog cross-check of auth schemes | `agent/composioCatalogCheck.py` | no |
| Verifier agent: tries to refute each claim | `agent/verifierAgent.py` | yes |
| Re-research of flagged apps with the exact problems | `agent/runVerification.py --step reresearch` | yes |
| Gold sample: 30 apps, 3 per category, fixed seed | `agent/goldSampler.py`, `agent/goldAssembler.py` | labels by AI agents |
| Scoring against the gold sample | `agent/accuracyScorer.py` | no |
| Pattern counts | `agent/patternAnalyzer.py` | no |
| Page | `agent/pageBuilder.py` + `agent/pageTemplate.html` | no |

Field definitions live in one file, `agent/labellingRubric.md`, used by the agent, the verifier and
the gold labellers alike.

## Honest limits

- What actually ran: the research agent on all apps it could finish (44 by Gemini, 56 by Claude Haiku sub-agents after Gemini throttled; PitchBook was read by hand in a browser because its pages return 403 to scripts (its MCP server is confirmed by its OAuth metadata; REST auth is a best guess) and QuickBooks was read by hand in a real browser because Intuit's pages are empty shells to scripts; the 15 Haiku records for reference apps are not scored). The evidence and catalog checks ran on every
  finished record. The verifier agent ran only on a 5-app trial. Re-research ran only on the 7 flagged
  reference apps, by Haiku sub-agents, because the Gemini run returned 503 for every call.
- Reference-set accuracy: 33/61 cells (54%) on the first pass, 44/61 (72%) after re-research, on the 15
  of 30 reference apps the Gemini agent finished. The re-research figure is likely optimistic because the
  re-researcher is the same model family that wrote the reference labels.

- The gold labels were written by independent AI agents reading live docs, not by a human. Cells they
  marked unsure are excluded from scoring, and the count is shown beside every accuracy figure.
- The research agent uses a free-tier Gemini model that was frequently overloaded; the client falls
  back through cheaper models and records which one answered each app.
- Composio's own `composio_search` toolkit returns HTTP 410 (retired), so web search runs through
  Composio's Tavily toolkit and pages are read by `agent/pageFetcher.py`.
- Pages that block automated fetching (for example PitchBook, QuickBooks) could not be read; those
  apps are marked with thin evidence rather than guessed.
