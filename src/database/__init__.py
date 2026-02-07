"""Database module for Job Application Agent."""

from .models import (
    Base, 
    Job, 
    Application, 
    ScrapingSession,
    Resume,
    InterviewPrep,
    AuditLog,
    UserPreferences,
    JobStatus,
    ApplicationStatus,
    ResumeVariant,
)
from .db import Database, get_database

__all__ = [
    "Base",
    "Job", 
    "Application",
    "ScrapingSession",
    "Resume",
    "InterviewPrep",
    "AuditLog",
    "UserPreferences",
    "JobStatus",
    "ApplicationStatus",
    "ResumeVariant",
    "Database",
    "get_database",
]

