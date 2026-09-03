"""CLI entrypoint: enrich vacancy skill relations in Notion.

Run from the project root::

    python main.py --all
    python main.py --page <notion_page_id>
    python main.py --index -1
    python main.py --page <notion_page_id> --preview
"""

import argparse
import logging
import sys

from notion_client import Client

from config import NOTION_SKILLS_DB_ID, NOTION_TOKEN, NOTION_VACANCIES_DB_ID
from enrich import enrich_all, enrich_vacancy, preview_vacancy_skills
from notion_read import (
    build_catalog,
    fetch_vacancy_page,
    get_database_data,
    list_vacancies_to_enrich,
)


def parse_args(argv=None):
    """Parse CLI arguments for enrich.

    :param argv: Argument list (default: ``sys.argv[1:]``).
    :type argv: list[str] | None
    :returns: Parsed args.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description=(
            "Enrich Vacancies: extract skills, match to catalog, write to Notion."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Enrich all vacancies with Description filled and Skills required empty",
    )
    group.add_argument(
        "--page",
        type=str,
        metavar="PAGE_ID",
        help="Notion page id of one Vacancy row",
    )
    group.add_argument(
        "--index",
        type=int,
        metavar="N",
        help="Index in Vacancies DB order (0-based; -1 = last)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Extract and match only; do not write to Notion",
    )
    parser.add_argument(
        "--method",
        choices=("llm", "regex"),
        default="llm",
        help="Extraction method (default: llm)",
    )
    return parser.parse_args(argv)


def _print_result(result):
    """Print a short enrich/preview summary to stdout."""
    vacancy = result["vacancy"]
    match = result["catalog_match"]
    print(f"title: {vacancy['title']}")
    print(f"id:    {vacancy['id']}")
    print(
        "required: matched="
        f"{len(match['required']['matched'])} "
        f"unknown={len(match['required']['unknown'])}"
    )
    print(
        "nice_to_have: matched="
        f"{len(match['nice_to_have']['matched'])} "
        f"unknown={len(match['nice_to_have']['unknown'])}"
    )
    if match["required"]["unknown"]:
        print(f"  unknown required: {match['required']['unknown']}")
    if match["nice_to_have"]["unknown"]:
        print(f"  unknown nice_to_have: {match['nice_to_have']['unknown']}")
    if "written" in result:
        if result["written"]:
            print("wrote: yes")
        else:
            print(f"wrote: no ({result.get('skipped')})")


def main(argv=None):
    """Run enrich CLI.

    :param argv: Optional CLI args (for tests); default reads ``sys.argv``.
    :type argv: list[str] | None
    :returns: Exit code (0 on success).
    :rtype: int
    """
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    notion = Client(auth=NOTION_TOKEN)
    catalog = build_catalog(get_database_data(notion, NOTION_SKILLS_DB_ID))

    if args.all:
        if args.preview:
            pages = list_vacancies_to_enrich(notion, NOTION_VACANCIES_DB_ID)
            print(f"candidates: {len(pages)}")
            for page in pages:
                result = preview_vacancy_skills(
                    page, catalog, method=args.method
                )
                _print_result(result)
                print("---")
            return 0

        results = enrich_all(
            notion, NOTION_VACANCIES_DB_ID, catalog, method=args.method
        )
        print(f"processed: {len(results)}")
        for result in results:
            _print_result(result)
            print("---")
        return 0

    page = fetch_vacancy_page(
        notion,
        NOTION_VACANCIES_DB_ID,
        index=args.index,
        page_id=args.page,
    )
    if args.preview:
        result = preview_vacancy_skills(page, catalog, method=args.method)
    else:
        result = enrich_vacancy(
            notion, page, catalog, method=args.method
        )
    _print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
