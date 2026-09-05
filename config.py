"""Load settings from environment variables (``.env`` via python-dotenv)."""

import os

from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_VACANCIES_DB_ID = os.getenv("NOTION_VACANCIES_DB_ID")
NOTION_SKILLS_DB_ID = os.getenv("NOTION_SKILLS_DB_ID")
NOTION_ROLES_DB_ID = os.getenv("NOTION_ROLES_DB_ID")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite"
)
