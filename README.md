# notion-vacancy-enrich

Python tooling to enrich **Vacancies** rows in Notion using the Notion API and Gemini structured output.

The current entrypoint (`main.py`) is a **dev compare script**: it runs regex-based and LLM-based skill extraction on one vacancy and writes side-by-side results under `local/compare/` for manual review.

Full enrichment (Role, Level, Work Mode, write-back to Notion) is planned as a separate MVP step.

## Stack

- Notion API (`notion-client`)
- Gemini JSON extraction (`google-genai`)
- Python 3, `python-dotenv`

## Project layout

| Module | Role |
|--------|------|
| `notion_read.py` | Read Notion databases/pages; build skills catalog; parse vacancies |
| `skill_extraction.py` | Extract skill names from vacancy text (LLM or regex) |
| `skill_match.py` | Match extracted names to catalog entries (`matched` / `unknown`) |
| `main.py` | Compare regex vs LLM on one vacancy; save review artifacts |
| `config.py` | Load settings from environment |

## Setup

1. Clone the repo and create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the env template and fill in your values:

   ```bash
   cp .env.example .env
   ```

   Required for the compare script:

   - `NOTION_TOKEN` — Notion integration token
   - `NOTION_VACANCIES_DB_ID` — Vacancies database ID
   - `NOTION_SKILLS_DB_ID` — Skills database ID
   - `GEMINI_API_KEY` — Gemini API key (for LLM extraction)
   - `GEMINI_MODEL` — optional; defaults to `gemini-3.5-flash-lite`

   `NOTION_ROLES_DB_ID` is reserved for the upcoming enrich MVP.

3. Grant the Notion integration access to the Vacancies and Skills databases.

## Usage

Pick one vacancy by index or by Notion page id:

```bash
python main.py --index 0
python main.py --index -1
python main.py --page <notion_page_id>
```

- `--index` — position in the Vacancies database query order (0-based). Negative indices count from the end (`-1` = last).
- `--page` — stable selector for a specific vacancy row.

Output is written to `local/compare/` (gitignored):

- `vacancy.txt` — title, id, and full description
- `regex.json` — regex extraction + catalog match
- `llm.json` — LLM extraction + catalog match

## Pipeline (one vacancy)

```
Notion read  →  extract (regex | LLM)  →  match to catalog  →  compare files
```

Regex finds catalog skill names that appear in the text (baseline). LLM splits skills into `required` and `nice_to_have` from the job description, then both paths are matched against the Notion Skills catalog.

## Status

- Done: Notion read, LLM skill extraction, regex baseline, catalog matching, compare CLI
- Planned: batch enrich, Role/Level/Work Mode extraction, write-back to Notion
