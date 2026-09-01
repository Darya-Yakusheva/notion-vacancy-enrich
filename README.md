# notion-vacancy-enrich

Python tooling to enrich **Vacancies** rows in Notion using the Notion API and Gemini structured output.

Finds vacancies with a filled **Description** and empty **Skills required**, extracts skills (LLM or regex), matches them to the Skills catalog, and writes relations back to Notion.

`main.py` is a separate **dev compare script**: regex vs LLM on one vacancy, with review files under `local/compare/`.

## Stack

- Notion API (`notion-client`)
- Gemini JSON extraction (`google-genai`)
- Python 3, `python-dotenv`

## Project layout

| Module | Role |
|--------|------|
| `notion_schema.py` | Vacancies DB property names (schema constants) |
| `notion_read.py` | Read databases/pages; list candidates; parse vacancies |
| `notion_write.py` | Build relation payloads; update Skills on a vacancy |
| `skill_extraction.py` | Extract skill names from text (LLM or regex) |
| `skill_match.py` | Match extracted names to catalog (`matched` / `unknown`) |
| `enrich.py` | Preview and enrich one or all candidate vacancies |
| `main.py` | Dev compare: regex vs LLM on one vacancy |
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

   Required:

   - `NOTION_TOKEN` — Notion integration token
   - `NOTION_VACANCIES_DB_ID` — Vacancies database ID
   - `NOTION_SKILLS_DB_ID` — Skills database ID
   - `GEMINI_API_KEY` — Gemini API key (for LLM extraction)
   - `GEMINI_MODEL` — optional; defaults to `gemini-3.5-flash-lite`

   `NOTION_ROLES_DB_ID` is optional and unused for now.

3. Grant the Notion integration access to the Vacancies and Skills databases.

## Enrich pipeline

```
list candidates  →  extract (regex | LLM)  →  match to catalog  →  write relations
```

A vacancy qualifies when **Description** has text and **Skills required** is empty.

`enrich_vacancy` skips the write when no required skills matched the catalog. Unknown names (not in the Skills DB) are logged separately for `required` and `nice_to_have`.

Example (from a small script or the Python REPL):

```python
import logging
from notion_client import Client

from config import NOTION_SKILLS_DB_ID, NOTION_TOKEN, NOTION_VACANCIES_DB_ID
from enrich import enrich_all, preview_vacancy_skills
from notion_read import build_catalog, get_database_data, list_vacancies_to_enrich

logging.basicConfig(level=logging.INFO)

notion = Client(auth=NOTION_TOKEN)
catalog = build_catalog(get_database_data(notion, NOTION_SKILLS_DB_ID))

# Preview one candidate (no Notion write)
pages = list_vacancies_to_enrich(notion, NOTION_VACANCIES_DB_ID)
preview = preview_vacancy_skills(pages[0], catalog)

# Enrich all candidates (writes to Notion)
results = enrich_all(notion, NOTION_VACANCIES_DB_ID, catalog)
```

## Compare script (dev)

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

Regex finds catalog skill names that appear in the text (baseline). LLM splits skills into `required` and `nice_to_have`, then both paths are matched against the Notion Skills catalog.

## Status

- Done: Notion read/write, skill extraction and matching, batch enrich, compare CLI
- Planned: UI to run enrichment without a separate Python script; review screen for skills found in a vacancy but missing from the Skills catalog (add manually or skip)
