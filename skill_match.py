"""Match extracted skill names against the Notion Skills catalog."""


def resolve_skills(names, catalog, by_lower=None):
    """Map skill names to catalog entries by case-insensitive exact name.

    Names that are not in the catalog are collected separately (not dropped).

    :param names: Skill names (e.g. from an LLM JSON response).
    :type names: list[str]
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :param by_lower: Optional precomputed ``name.lower()`` to skill map; built
        from ``catalog`` when omitted.
    :type by_lower: dict[str, dict] | None
    :returns: Tuple ``(matched, unknown)`` — catalog dicts and unmatched names,
        both sorted.
    :rtype: tuple[list[dict], list[str]]
    """
    if by_lower is None:
        by_lower = {skill["name"].strip().lower(): skill for skill in catalog}
    matches = []
    unknown = []
    seen = set()
    for name in names:
        cleaned = name.strip()
        key = cleaned.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        skill = by_lower.get(key)
        if skill:
            matches.append(skill)
        else:
            unknown.append(cleaned)
    return (
        sorted(matches, key=lambda skill: skill["name"].lower()),
        sorted(unknown, key=str.lower),
    )


def match_extracted_skills(extracted, catalog):
    """Resolve extracted skill names against the Notion catalog.

    :param extracted: Dict with ``required`` and ``nice_to_have`` name lists.
    :type extracted: dict
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :returns: For each group, dict with ``matched`` catalog entries and
        ``unknown`` names.
    :rtype: dict
    """
    by_lower = {skill["name"].strip().lower(): skill for skill in catalog}
    required_matched, required_unknown = resolve_skills(
        extracted.get("required", []), catalog, by_lower=by_lower
    )
    nice_matched, nice_unknown = resolve_skills(
        extracted.get("nice_to_have", []), catalog, by_lower=by_lower
    )
    return {
        "required": {
            "matched": required_matched,
            "unknown": required_unknown,
        },
        "nice_to_have": {
            "matched": nice_matched,
            "unknown": nice_unknown,
        },
    }
