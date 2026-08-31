"""Extract skill names from a vacancy description (LLM or regex)."""

import json
import re

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL

SKILLS_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "required": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "nice_to_have": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": ["required", "nice_to_have"],
}

SKILLS_PROMPT_INSTRUCTIONS = (
    "You extract skills from a job vacancy description.\n"
    "Look at the whole text, including responsibility sections even when they "
    "are not clearly titled. Headings may vary or be missing, for example: "
    "What you will do, Responsibilities, In this role, Your role, Key tasks, "
    "or bullet lists of duties.\n"
    "Cover all of these kinds of skills when they appear in the text:\n"
    "- tools (e.g. Docker, Ansible, Terraform, VS Code)\n"
    "- technologies / platforms (e.g. Redis, Kubernetes, NoSQL, REST APIs)\n"
    "- domain knowledge (e.g. Distributed Systems, Data Platform)\n"
    "- methodologies / practices (e.g. Containerization, Orchestration, "
    "Automation, Scripting, Agile)\n"
    "- soft skills when clearly stated (e.g. Communication, Problem-solving)\n"
    "If the text mentions both a concrete tool and an abstract skill "
    "(e.g. Docker/Kubernetes for containerization and orchestration), "
    "include BOTH the tools and the abstract skills — do not drop one "
    "because the other is present.\n"
    "Return ONLY skills that are explicitly stated or clearly evidenced in the "
    "text. Do not invent skills, do not add a typical stack, and do not guess.\n"
    "Split skills into two lists by where they appear in the vacancy:\n"
    "- required: skills from requirements / must-have / profile / "
    "\"we believe the right profile\" / qualifications sections "
    "(and anything explicitly marked required)\n"
    "- nice_to_have: skills from duty/responsibility sections such as "
    "What you will do, Responsibilities, In this role, Your role, Key tasks, "
    "or similar duty bullet lists — including skills clearly implied by those "
    "duties (e.g. 'developing Python applications' → Python). Also put here "
    "skills marked preferred / nice to have / plus / bonus / optional.\n"
    "If the same skill appears in both a requirements section and a duties "
    "section, put it only in required.\n"
    "Never put the same skill in both lists.\n"
    "Use short skill names (e.g. Python, SQL, Docker, Containerization), "
    "not full sentences.\n"
    "If no skills are found for a list, return an empty array."
)


def build_skills_prompt(description):
    """Build the Gemini prompt for skill extraction.

    :param description: Vacancy description text.
    :type description: str
    :returns: Full prompt string.
    :rtype: str
    """
    return (
        f"{SKILLS_PROMPT_INSTRUCTIONS}\n\n"
        f"Vacancy description:\n{description}\n"
    )


def call_gemini_json(prompt, schema, model=None):
    """Call Gemini and parse a JSON object from the response.

    :param prompt: Full prompt text.
    :type prompt: str
    :param schema: Response schema for structured JSON output.
    :type schema: dict
    :param model: Gemini model code (default: ``GEMINI_MODEL`` env var).
    :type model: str | None
    :returns: Parsed JSON object.
    :rtype: dict
    :raises ValueError: If ``GEMINI_API_KEY`` is missing.
    :raises RuntimeError: If the Gemini request or JSON parse fails.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")

    model_id = model or GEMINI_MODEL
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
                "temperature": 0,
            },
        )
        return json.loads(response.text)
    except Exception as exc:
        raise RuntimeError(f"Gemini request failed: {exc}") from exc


def extract_skills_llm(description, model=None):
    """Extract required and nice-to-have skill names from a vacancy via LLM.

    Does not use the Notion catalog. Catalog matching is a separate step
    (:mod:`skill_match`).

    :param description: Vacancy description text.
    :type description: str
    :param model: Gemini model code (default: ``GEMINI_MODEL`` env var).
    :type model: str | None
    :returns: Dict with ``required`` and ``nice_to_have`` lists of skill names.
    :rtype: dict
    :raises ValueError: If ``GEMINI_API_KEY`` is missing.
    :raises RuntimeError: If the Gemini request or JSON parse fails.
    """
    prompt = build_skills_prompt(description)
    payload = call_gemini_json(prompt, SKILLS_RESPONSE_SCHEMA, model=model)
    return {
        "required": payload.get("required", []),
        "nice_to_have": payload.get("nice_to_have", []),
    }


def match_skills_by_regex(description, catalog):
    """Find catalog skills whose names appear in ``description``.

    Matching is case-insensitive. The skill name must be a whole token
    (not a substring of a longer word), so ``AI`` does not match ``MAINTAIN``.

    :param description: Vacancy description text.
    :type description: str
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :returns: Matching skill dicts (keys ``id``, ``name``), sorted by name.
    :rtype: list[dict]
    """
    matches = []
    for skill in catalog:
        name = skill["name"].strip()
        if not name:
            continue
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(pattern, description, flags=re.IGNORECASE):
            matches.append(skill)
    return sorted(matches, key=lambda skill: skill["name"].lower())


def extract_skills_regex(description, catalog):
    """Extract skill names from text by matching against the catalog (regex).

    Same return shape as :func:`extract_skills_llm`.
    Regex cannot split required vs nice-to-have: all hits go in ``required``.

    :param description: Vacancy description text.
    :type description: str
    :param catalog: Skill dicts from :func:`notion_read.build_catalog`.
    :type catalog: list[dict]
    :returns: Dict with ``required`` (skill names) and empty ``nice_to_have``.
    :rtype: dict
    """
    matched = match_skills_by_regex(description, catalog)
    return {
        "required": [skill["name"] for skill in matched],
        "nice_to_have": [],
    }
