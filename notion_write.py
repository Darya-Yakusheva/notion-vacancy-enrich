"""Write enriched data back to Notion."""

from notion_schema import SKILLS_NICE_TO_HAVE_PROPERTY, SKILLS_REQUIRED_PROPERTY


def build_relation_payload(page_ids):
    """Build a Notion ``relation`` property value for ``pages.update``.

    Example use with :data:`notion_schema.SKILLS_REQUIRED_PROPERTY`::

        properties={
            SKILLS_REQUIRED_PROPERTY: build_relation_payload(skill_ids),
        }

    :param page_ids: Notion page IDs to link (e.g. skill row ids from catalog).
    :type page_ids: list[str]
    :returns: Property value dict with key ``relation``.
    :rtype: dict
    """
    return {"relation": [{"id": page_id} for page_id in page_ids]}


def update_vacancy_skills(notion, page_id, *, required_ids, nice_to_have_ids=None):
    """Write skill relations to a Vacancy page via ``pages.update``.

    :param notion: Authenticated Notion client.
    :type notion: notion_client.Client
    :param page_id: Notion page id of the Vacancy row.
    :type page_id: str
    :param required_ids: Skill page ids for :data:`notion_schema.SKILLS_REQUIRED_PROPERTY`.
    :type required_ids: list[str]
    :param nice_to_have_ids: Skill page ids for :data:`notion_schema.SKILLS_NICE_TO_HAVE_PROPERTY`;
        when ``None``, that property is not updated.
    :type nice_to_have_ids: list[str] | None
    :returns: Updated page dict from the Notion API.
    :rtype: dict
    """
    properties = {
        SKILLS_REQUIRED_PROPERTY: build_relation_payload(required_ids),
    }
    if nice_to_have_ids is not None:
        properties[SKILLS_NICE_TO_HAVE_PROPERTY] = build_relation_payload(
            nice_to_have_ids
        )
    return notion.pages.update(page_id, properties=properties)
