# Florida University P3 Opportunity Agent

Simple Replit-ready web app for generating CEO-review materials for Florida university public-private partnership opportunities.

The app generates documents only. It does not submit proposals, email universities, contact public officials, or provide legal advice.

## What You Get

From the dashboard you can:

- Run University P3 Agent
- View Past Reports
- Download Latest Report

Each run creates a timestamped folder inside `outputs/` with:

- `CEO_university_p3_opportunity_report.md`
- `ranked_university_p3_sites.xlsx`
- `ranked_university_p3_sites.csv`
- `draft_unsolicited_proposal_package.md`
- `university_p3_opportunity_reports.json`

The draft unsolicited proposal is for CEO review only and must be reviewed by counsel before any outreach or submission.

## Replit Setup

1. Create a new Replit project.
2. Choose **Python** as the template.
3. Upload or import these top-level project files into Replit:
   - `main.py`
   - `app.py`
   - `p3_agent_system.py`
   - `requirements.txt`
   - `.replit`
   - `README.md`
   - `outputs/.gitkeep`
4. Confirm these files are at the project root, not inside a nested folder.
5. In Replit, open the **Secrets** or **Environment Variables** panel.
6. Add the API keys you want to use:
   - `OPENAI_API_KEY`
   - `TAVILY_API_KEY` or `PERPLEXITY_API_KEY`
   - `ANTHROPIC_API_KEY` only if you later add Anthropic support
7. Optional: add `P3_SEARCH_PROVIDER` with one of:
   - `auto`
   - `tavily`
   - `perplexity`
   - `serpapi`
   - `bing`
   - `none`
8. Click **Run**.
9. Replit will install packages from `requirements.txt` and run `python main.py`.
10. Open the web preview.
11. Click **Run University P3 Agent**.

No Docker is required. No AWS is required.

## Replit Run Command

The `.replit` file is already configured as:

```text
run = "python main.py"
```

If Replit asks for a run command manually, enter:

```bash
python main.py
```

## If You Do Not Add Search Keys

The dashboard will still work. If no search key is configured, it automatically uses demo fixture data so you can confirm the app runs and produces files.

For real research, add at least one search key:

- `TAVILY_API_KEY`, or
- `PERPLEXITY_API_KEY`

## Environment Variables

Required for LLM drafting:

```text
OPENAI_API_KEY
```

Optional search keys:

```text
TAVILY_API_KEY
PERPLEXITY_API_KEY
SERPAPI_API_KEY
BING_SEARCH_API_KEY
```

Optional app settings:

```text
P3_SEARCH_PROVIDER=auto
P3_USE_FIXTURE_DATA=false
P3_OUTPUT_DIR=./outputs
OPENAI_MODEL=gpt-4.1
CEO_NAME=CEO
```

`ANTHROPIC_API_KEY` is loaded for future use if Anthropic support is added later, but the current app uses OpenAI plus deterministic fallbacks.

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
python main.py
```

Open:

```text
http://localhost:8000
```

## Safety Notes

- Do not submit any generated proposal without counsel review.
- Verify title, ownership, procurement rules, board approval requirements, zoning, bond/tax issues, and public records implications.
- The app is a research and drafting assistant, not a legal, tax, bond, or procurement opinion.
