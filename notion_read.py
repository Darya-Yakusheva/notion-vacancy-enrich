"""Read data from Notion (databases, pages, properties)."""

from notion_schema import DESCRIPTION_PROPERTY, SKILLS_REQUIRED_PROPERTY


def plain_text(rich_text):
    """Join Notion ``rich_text`` parts into a single string.

    :param rich_text: Notion ``rich_text`` array from a page property.
    :type rich_text: list
    :returns: Concatenated plain text.
    :rtype: str
    """
    return "".join(part["plain_text"] for part in rich_text)


def title_of_page(page):
    """Return the title property value of a Notion page.

    Works for any database row (Skill, Role, Vacancy, etc.) without
    hardcoding the property name.

    :param page: Notion page object from a query response.
    :type page: dict
    :returns: Title text.
    :rtype: str
    :raises ValueError: If the page has no title property.
    """
    for prop in page["properties"].values():
        if prop.get("type") == "title":
            return plain_text(prop["title"])
    raise ValueError("no title")


def get_database_data(notion, database_id):
    """Fetch all pages from a Notion database, handling pagination.

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param database_id: Notion database ID from ``.env``.
    :type database_id: str
    :returns: All page objects from the database.
    :rtype: list
    """
    database = notion.databases.retrieve(database_id)
    datasource_id = database["data_sources"][0]["id"]

    all_pages = []
    start_cursor = None
    while True:
        kwargs = {"start_cursor": start_cursor} if start_cursor else {}
        response = notion.data_sources.query(datasource_id, **kwargs)
        all_pages.extend(response["results"])
        if not response["has_more"]:
            break
        start_cursor = response["next_cursor"]
    return all_pages


def build_catalog(pages):
    """Build a lookup list from Notion page objects.

    :param pages: Page objects from :func:`get_database_data`.
    :type pages: list
    :returns: List of dicts with keys ``id`` and ``name``.
    :rtype: list[dict]
    """
    return [{"id": page["id"], "name": title_of_page(page)} for page in pages]


def rich_text_is_empty(page, property_name):
    """Return whether a Notion ``rich_text`` property has no text content.

    Treats whitespace-only text as empty.

    :param page: Notion page object from a query response.
    :type page: dict
    :param property_name: Property key in ``page['properties']``, e.g.
        :data:`DESCRIPTION_PROPERTY`.
    :type property_name: str
    :returns: ``True`` if there is no non-whitespace text.
    :rtype: bool
    :raises KeyError: If the property is missing on the page.
    :raises ValueError: If the property is not ``rich_text``.
    """
    prop = page["properties"][property_name]
    if prop.get("type") != "rich_text":
        raise ValueError(f"{property_name!r} is not rich_text")
    return not plain_text(prop.get("rich_text", [])).strip()


def relation_is_empty(page, property_name):
    """Return whether a Notion ``relation`` property has no linked pages.

    In the Vacancies database, ``Skills required`` and ``Skills nice to have``
    are relations to rows in the Skills database. Each linked skill is one
    entry in the property's ``relation`` list (with a Notion ``id``).

    For enrichment, call with :data:`SKILLS_REQUIRED_PROPERTY` to skip vacancies
    that already have required skills set.

    :param page: Notion page object from a query response.
    :type page: dict
    :param property_name: Property key in ``page['properties']``, e.g.
        ``Skills required``.
    :type property_name: str
    :returns: ``True`` if the relation list is empty.
    :rtype: bool
    :raises KeyError: If the property is missing on the page.
    :raises ValueError: If the property is not ``relation``.
    """
    prop = page["properties"][property_name]
    if prop.get("type") != "relation":
        raise ValueError(f"{property_name!r} is not relation")
    return len(prop.get("relation", [])) == 0


def vacancy_needs_skill_enrich(page):
    """Return whether a vacancy should get ``Skills required`` enrichment.

    A vacancy qualifies when :data:`DESCRIPTION_PROPERTY` has text and
    :data:`SKILLS_REQUIRED_PROPERTY` has no linked skills.

    :param page: Vacancy page object from Notion.
    :type page: dict
    :returns: ``True`` if description is filled and required skills are empty.
    :rtype: bool
    """
    return (
        not rich_text_is_empty(page, DESCRIPTION_PROPERTY)
        and relation_is_empty(page, SKILLS_REQUIRED_PROPERTY)
    )


def list_vacancies_to_enrich(notion, database_id):
    """Return vacancy pages that need ``Skills required`` enrichment.

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param database_id: Vacancies database ID from ``.env``.
    :type database_id: str
    :returns: Raw Notion page dicts matching :func:`vacancy_needs_skill_enrich`.
    :rtype: list[dict]
    """
    pages = get_database_data(notion, database_id)
    return [page for page in pages if vacancy_needs_skill_enrich(page)]


def fetch_vacancy_page(notion, database_id, *, index=None, page_id=None):
    """Fetch one raw Vacancy page from Notion (API shape, not parsed).

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param database_id: Vacancies database ID from ``.env``.
    :type database_id: str
    :param index: Index in Vacancies DB query order (supports negative indices).
    :type index: int | None
    :param page_id: Notion page id of a Vacancy row.
    :type page_id: str | None
    :returns: Full page dict as returned by the Notion API.
    :rtype: dict
    :raises ValueError: If neither or both selectors are given, or index is
        out of range.
    """
    if (index is None) == (page_id is None):
        raise ValueError("provide exactly one of index or page_id")

    if page_id is not None:
        return notion.pages.retrieve(page_id.strip())

    pages = get_database_data(notion, database_id)
    try:
        return pages[index]
    except IndexError as exc:
        raise ValueError(
            f"index {index} out of range "
            f"(-{len(pages)}..{len(pages) - 1}, {len(pages)} vacancies)"
        ) from exc


def parse_vacancy(page):
    """Extract id, title, and description from a Vacancy page.

    :param page: Vacancy page object from Notion.
    :type page: dict
    :returns: Dict with keys ``id``, ``title``, ``description``.
    :rtype: dict
    :raises KeyError: If the ``Description`` property is missing.
    :raises ValueError: If ``Description`` is not ``rich_text``.
    """
    description = page["properties"][DESCRIPTION_PROPERTY]
    if description.get("type") != "rich_text":
        raise ValueError(f"{DESCRIPTION_PROPERTY!r} is not rich_text")
    return {
        "id": page["id"],
        "title": title_of_page(page),
        "description": plain_text(description["rich_text"]),
    }
