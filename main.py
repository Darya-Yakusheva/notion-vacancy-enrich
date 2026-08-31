"""Compare regex vs LLM skill extraction on one vacancy.

Dev helper: writes review files under ``local/compare/``.

Run::

    python main.py --index 25
    python main.py --page <notion_page_id>
"""

import argparse
import json
from pathlib import Path

from notion_client import Client

from config import (
    GEMINI_MODEL,
    NOTION_SKILLS_DB_ID,
    NOTION_TOKEN,
    NOTION_VACANCIES_DB_ID,
)
from notion_read import build_catalog, fetch_vacancy_page, get_database_data, parse_vacancy
from skill_extraction import extract_skills_llm, extract_skills_regex
from skill_match import match_extracted_skills

COMPARE_DIR = Path("local/compare")


def parse_args(argv=None):
    """Parse CLI arguments for vacancy selection.

    :param argv: Argument list (default: ``sys.argv[1:]``).
    :type argv: list[str] | None
    :returns: Parsed args with ``index`` or ``page`` set.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="Compare regex vs LLM skill extraction on one vacancy.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--index",
        type=int,
        metavar="N",
        help="Index in Vacancies DB order (0-based; -1 = last, -2 = second to last)",
    )
    group.add_argument(
        "--page",
        type=str,
        metavar="PAGE_ID",
        help="Notion page id of a Vacancy row",
    )
    return parser.parse_args(argv)


def load_vacancy(notion, *, index=None, page_id=None):
    """Load and parse one vacancy by database index or Notion page id.

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param index: Index in the Vacancies DB query results (0-based; negative
        counts from the end, e.g. ``-1`` for the last vacancy).
    :type index: int | None
    :param page_id: Notion page id of a Vacancy row.
    :type page_id: str | None
    :returns: Dict with keys ``id``, ``title``, ``description``.
    :rtype: dict
    :raises ValueError: If neither selector is set, both are set, or index is
        out of range.
    """
    page = fetch_vacancy_page(
        notion, NOTION_VACANCIES_DB_ID, index=index, page_id=page_id
    )
    return parse_vacancy(page)


def run_extraction(method, description, catalog, model=None):
    """Extract skills and match them to the catalog.

    :param method: Extraction method: ``regex`` or ``llm``.
    :type method: str
    :param description: Vacancy description text.
    :type description: str
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :param model: Gemini model code for ``llm`` (ignored for ``regex``).
    :type model: str | None
    :returns: Dict with keys ``method``, ``model``, ``raw``, ``catalog_match``.
    :rtype: dict
    :raises ValueError: If ``method`` is not ``regex`` or ``llm``.
    """
    if method == "regex":
        raw = extract_skills_regex(description, catalog)
        model = None
    elif method == "llm":
        raw = extract_skills_llm(description, model=model)
    else:
        raise ValueError(f"unknown method: {method!r}")

    return {
        "method": method,
        "model": model,
        "raw": raw,
        "catalog_match": match_extracted_skills(raw, catalog),
    }


def save_compare(out_dir, vacancy, regex_result, llm_result):
    """Write vacancy text and regex/LLM JSON under ``out_dir``.

    :param out_dir: Output directory (created if missing).
    :type out_dir: Path | str
    :param vacancy: Parsed vacancy with ``id``, ``title``, ``description``.
    :type vacancy: dict
    :param regex_result: Result of :func:`run_extraction` for ``regex``.
    :type regex_result: dict
    :param llm_result: Result of :func:`run_extraction` for ``llm``.
    :type llm_result: dict
    :returns: Paths written: vacancy txt, regex json, llm json.
    :rtype: list[Path]
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    vacancy_txt = out_dir / "vacancy.txt"
    regex_json = out_dir / "regex.json"
    llm_json = out_dir / "llm.json"

    vacancy_txt.write_text(
        f"Title: {vacancy['title']}\n"
        f"ID: {vacancy['id']}\n\n"
        f"--- Description ---\n\n"
        f"{vacancy['description']}\n",
        encoding="utf-8",
    )
    for path, data in ((regex_json, regex_result), (llm_json, llm_result)):
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return [vacancy_txt, regex_json, llm_json]


def print_summary(vacancy, regex_result, llm_result, paths):
    """Print a short compare summary to stdout.

    :param vacancy: Parsed vacancy (uses ``title``).
    :type vacancy: dict
    :param regex_result: Result of :func:`run_extraction` for ``regex``.
    :type regex_result: dict
    :param llm_result: Result of :func:`run_extraction` for ``llm``.
    :type llm_result: dict
    :param paths: File paths from :func:`save_compare`.
    :type paths: list[Path]
    """
    def counts(result):
        raw = result["raw"]
        return len(raw["required"]), len(raw["nice_to_have"])

    r_req, r_nice = counts(regex_result)
    l_req, l_nice = counts(llm_result)
    print(f"title: {vacancy['title']}")
    print(f"regex: required={r_req} | nice_to_have={r_nice}")
    print(f"llm: required={l_req} | nice_to_have={l_nice}")
    print(f"model: {llm_result['model']}")
    print("wrote:")
    for path in paths:
        print(f"  {path}")


def main(argv=None):
    """Run regex and LLM on one vacancy; save outputs for side-by-side review.

    :param argv: Optional CLI args (for tests); default reads ``sys.argv``.
    :type argv: list[str] | None
    """
    args = parse_args(argv)
    notion = Client(auth=NOTION_TOKEN)
    catalog = build_catalog(get_database_data(notion, NOTION_SKILLS_DB_ID))
    vacancy = load_vacancy(notion, index=args.index, page_id=args.page)
    description = vacancy["description"]

    regex_result = run_extraction("regex", description, catalog)
    llm_result = run_extraction("llm", description, catalog, model=GEMINI_MODEL)

    paths = save_compare(COMPARE_DIR, vacancy, regex_result, llm_result)
    print_summary(vacancy, regex_result, llm_result, paths)


if __name__ == "__main__":
    main()
