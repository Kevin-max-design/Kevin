"""Applicator module for Job Application Agent."""

from .form_filler import FormFiller
from .manager import ApplicationManager
from .playwright_applicator import PlaywrightApplicator, SyncPlaywrightApplicator, ApplicationResult

__all__ = [
    "FormFiller",
    "ApplicationManager",
    "PlaywrightApplicator",
    "SyncPlaywrightApplicator",
    "ApplicationResult",
]

