# notion-vacancy-enrich

Python tooling to enrich **Vacancies** rows in Notion using the Notion API and Gemini structured output.

Finds vacancies with a filled **Description** and empty **Skills required**, extracts skills (LLM or regex), matches them to the Skills catalog, and writes relations back to Notion.

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
| `main.py` | CLI entrypoint for enrich |
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
   - `GEMINI_FALLBACK_MODEL` — optional; defaults to `gemini-3.1-flash-lite`
     (used once on 429/503 from the primary model)

3. Grant the Notion integration access to the Vacancies and Skills databases.

## Usage

Enrich writes **Skills required** and **Skills nice to have** for vacancies that have a filled Description and empty Skills required (for `--all`).

```bash
# All candidates
python main.py --all

# One vacancy by Notion page id
python main.py --page <notion_page_id>

# One vacancy by index in DB query order (-1 = last)
python main.py --index -1

# Extract + match only (no Notion write)
python main.py --page <notion_page_id> --preview

# Use regex instead of LLM
python main.py --page <notion_page_id> --method regex

# See all available flags
python main.py --help
```

Unknown skill names (found in the text, missing from the Skills catalog) are printed in the terminal, separately for `required` and `nice_to_have`.

## Pipeline

```
select vacancy(ies)  →  extract (LLM | regex)  →  match to catalog  →  write relations
```

`enrich_vacancy` skips the write when no required skills matched the catalog.

## Status

- Done: Notion read/write, skill extraction and matching, batch/single enrich CLI
- Planned: review screen for skills found in a vacancy but missing from the Skills catalog (add manually or skip)
