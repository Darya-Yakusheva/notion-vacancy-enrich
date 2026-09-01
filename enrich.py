"""Enrich vacancy skill relations (preview and write)."""

import logging

from config import GEMINI_MODEL
from notion_read import list_vacancies_to_enrich, parse_vacancy
from notion_write import update_vacancy_skills
from skill_extraction import extract_skills_llm, extract_skills_regex
from skill_match import match_extracted_skills

logger = logging.getLogger(__name__)


def preview_vacancy_skills(page, catalog, *, method="llm", model=None):
    """Extract and match skills for one vacancy without writing to Notion.

    :param page: Raw Vacancy page from Notion.
    :type page: dict
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :param method: Extraction method: ``regex`` or ``llm``.
    :type method: str
    :param model: Gemini model code for ``llm``; defaults to :data:`GEMINI_MODEL`.
        Ignored for ``regex``.
    :type model: str | None
    :returns: Dict with keys ``vacancy``, ``method``, ``model``, ``raw``,
        ``catalog_match``.
    :rtype: dict
    :raises ValueError: If ``method`` is not ``regex`` or ``llm``.
    """
    vacancy = parse_vacancy(page)
    description = vacancy["description"]

    if method == "regex":
        raw = extract_skills_regex(description, catalog)
        model = None
    elif method == "llm":
        if model is None:
            model = GEMINI_MODEL
        raw = extract_skills_llm(description, model=model)
    else:
        raise ValueError(f"unknown method: {method!r}")

    return {
        "vacancy": vacancy,
        "method": method,
        "model": model,
        "raw": raw,
        "catalog_match": match_extracted_skills(raw, catalog),
    }


def enrich_vacancy(notion, page, catalog, *, method="llm", model=None):
    """Extract, match, and write skill relations for one vacancy.

    Does not write when ``required`` matched is empty. Logs unknown skill
    names separately for required and nice to have.

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param page: Raw Vacancy page from Notion.
    :type page: dict
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :param method: Extraction method: ``regex`` or ``llm``.
    :type method: str
    :param model: Gemini model code for ``llm``; defaults to :data:`GEMINI_MODEL`.
    :type model: str | None
    :returns: Dict with keys from :func:`preview_vacancy_skills` plus
        ``written``, ``skipped``, ``updated``.
    :rtype: dict
    """
    preview = preview_vacancy_skills(page, catalog, method=method, model=model)
    match = preview["catalog_match"]
    title = preview["vacancy"]["title"]
    required_ids = [skill["id"] for skill in match["required"]["matched"]]
    nice_ids = [skill["id"] for skill in match["nice_to_have"]["matched"]]

    if match["required"]["unknown"]:
        logger.info(
            "%s: unknown required skills %s",
            title,
            match["required"]["unknown"],
        )
    if match["nice_to_have"]["unknown"]:
        logger.info(
            "%s: unknown nice_to_have skills %s",
            title,
            match["nice_to_have"]["unknown"],
        )

    if not required_ids:
        logger.warning("%s: skip write — no matched required skills", title)
        return {
            **preview,
            "written": False,
            "skipped": "no_required_matches",
            "updated": None,
        }

    updated = update_vacancy_skills(
        notion,
        preview["vacancy"]["id"],
        required_ids=required_ids,
        nice_to_have_ids=nice_ids,
    )
    logger.info(
        "%s: wrote required=%d, nice_to_have=%d",
        title,
        len(required_ids),
        len(nice_ids),
    )
    return {**preview, "written": True, "skipped": None, "updated": updated}


def enrich_all(notion, database_id, catalog, *, method="llm", model=None):
    """Enrich all vacancies that need ``Skills required`` filled.

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param database_id: Vacancies database ID from ``.env``.
    :type database_id: str
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :param method: Extraction method: ``regex`` or ``llm``.
    :type method: str
    :param model: Gemini model code for ``llm``; defaults to :data:`GEMINI_MODEL`.
    :type model: str | None
    :returns: List of :func:`enrich_vacancy` result dicts, one per page.
    :rtype: list[dict]
    """
    pages = list_vacancies_to_enrich(notion, database_id)
    results = []
    for page in pages:
        results.append(
            enrich_vacancy(notion, page, catalog, method=method, model=model)
        )
    return results
