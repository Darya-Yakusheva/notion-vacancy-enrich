"""Read data from Notion (databases, pages, properties)."""


def plain_text(rich_text):
    """Join Notion ``rich_text`` parts into a single string.

    :param rich_text: Notion rich_text array from a page property.
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
    :returns: List of ``{"id": page_id, "name": title}`` dicts.
    :rtype: list[dict]
    """
    return [{"id": page["id"], "name": title_of_page(page)} for page in pages]


def parse_vacancy(page):
    """Extract id, title, and description from a Vacancy page.

    :param page: Vacancy page object from Notion.
    :type page: dict
    :returns: ``{"id", "title", "description"}``.
    :rtype: dict
    :raises KeyError: If the ``Description`` property is missing.
    :raises ValueError: If ``Description`` is not ``rich_text``.
    """
    description = page["properties"]["Description"]
    if description.get("type") != "rich_text":
        raise ValueError("'Description' is not rich_text")
    return {
        "id": page["id"],
        "title": title_of_page(page),
        "description": plain_text(description["rich_text"]),
    }
