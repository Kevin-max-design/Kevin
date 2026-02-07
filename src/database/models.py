"""
Database Models for Job Application Agent

Comprehensive models for jobs, applications, resumes, interview prep, and audit logging.
Supports semantic matching, human-in-the-loop workflows, and application tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, 
    Text, Boolean, ForeignKey, LargeBinary, Index, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()


# Enums for status tracking
class JobStatus(enum.Enum):
    NEW = "new"
    MATCHED = "matched"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    CLOSED = "closed"


class ApplicationStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    FAILED = "failed"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class ResumeVariant(enum.Enum):
    DEFAULT = "default"
    DATA_SCIENCE = "data_science"
    MACHINE_LEARNING = "machine_learning"
    UIUX = "uiux"
    INTERNSHIP = "internship"
    GENERAL = "general"


class Job(Base):
    """Represents a scraped job listing with semantic matching support."""
    
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job details
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    description = Column(Text)
    requirements = Column(Text)
    
    # Job metadata
    url = Column(String(500), nullable=False, unique=True)
    platform = Column(String(50), nullable=False)  # linkedin, indeed, etc.
    job_type = Column(String(50))  # full-time, internship, contract
    work_mode = Column(String(50))  # remote, hybrid, onsite
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String(10))
    application_email = Column(String(255))  # For email-based applications
    
    # Semantic matching
    match_score = Column(Float, default=0.0)
    semantic_score = Column(Float, default=0.0)  # Embedding-based similarity
    matched_skills = Column(Text)  # JSON array of matched skills
    missing_skills = Column(Text)  # JSON array of skills not in resume
    embedding = Column(LargeBinary)  # Stored embedding vector for JD
    
    # Human-in-the-loop workflow
    status = Column(String(50), default="new")  # new, matched, approved, rejected, applied, interview, offer
    is_approved = Column(Boolean, default=False)
    approval_notes = Column(Text)
    is_easy_apply = Column(Boolean, default=False)
    
    # Resume selection
    selected_resume_id = Column(Integer, ForeignKey("resumes.id"))
    
    # Timestamps
    posted_date = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    matched_at = Column(DateTime)
    approved_at = Column(DateTime)
    applied_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = relationship("Application", back_populates="job")
    selected_resume = relationship("Resume", foreign_keys=[selected_resume_id])
    interview_preps = relationship("InterviewPrep", back_populates="job")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_match_score', 'match_score'),
        Index('idx_job_platform', 'platform'),
    )
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "url": self.url,
            "platform": self.platform,
            "job_type": self.job_type,
            "work_mode": self.work_mode,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "match_score": self.match_score,
            "semantic_score": self.semantic_score,
            "matched_skills": json.loads(self.matched_skills) if self.matched_skills else [],
            "missing_skills": json.loads(self.missing_skills) if self.missing_skills else [],
            "status": self.status,
            "is_approved": self.is_approved,
            "is_easy_apply": self.is_easy_apply,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }
    
    def set_matched_skills(self, skills: List[str]):
        self.matched_skills = json.dumps(skills)
    
    def set_missing_skills(self, skills: List[str]):
        self.missing_skills = json.dumps(skills)


class Application(Base):
    """Represents a job application with full tracking."""
    
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    
    # Application content
    cover_letter = Column(Text)
    tailored_resume_path = Column(String(500))  # Path to tailored resume file
    
    # Application method
    application_method = Column(String(50), default="form")  # form, email, easy_apply
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, approved, submitted, failed, interview, offer
    submission_result = Column(Text)  # JSON with submission details
    response_received = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    applied_at = Column(DateTime)
    response_at = Column(DateTime)
    
    # Notes and feedback
    notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    resume = relationship("Resume")
    
    def __repr__(self):
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "resume_id": self.resume_id,
            "status": self.status,
            "application_method": self.application_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "response_received": self.response_received,
            "notes": self.notes,
        }


class ScrapingSession(Base):
    """Tracks scraping sessions for analytics."""
    
    __tablename__ = "scraping_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    status = Column(String(50), default="running")  # running, completed, failed
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<ScrapingSession(id={self.id}, platform='{self.platform}', jobs_found={self.jobs_found})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "jobs_found": self.jobs_found,
            "jobs_new": self.jobs_new,
            "status": self.status,
        }


class Resume(Base):
    """Stores resume versions with extracted data and embeddings."""
    
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Resume identification
    name = Column(String(255), nullable=False)  # e.g., "Data Science Resume v2"
    variant = Column(String(50), default="default")  # data_science, machine_learning, uiux, internship
    
    # File storage
    file_path = Column(String(500))
    file_type = Column(String(10))  # pdf, docx
    
    # Extracted content
    raw_text = Column(Text)
    skills = Column(Text)  # JSON array of extracted skills
    experience_years = Column(Float)
    education = Column(Text)  # JSON with education details
    
    # Semantic matching
    embedding = Column(LargeBinary)  # Stored embedding vector
    
    # Metadata
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Resume(id={self.id}, name='{self.name}', variant='{self.variant}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "variant": self.variant,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "skills": json.loads(self.skills) if self.skills else [],
            "experience_years": self.experience_years,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def set_skills(self, skills: List[str]):
        self.skills = json.dumps(skills)
    
    def get_skills(self) -> List[str]:
        return json.loads(self.skills) if self.skills else []


class InterviewPrep(Base):
    """Interview preparation materials for a specific job."""
    
    __tablename__ = "interview_preps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    # Generated content (all stored as JSON)
    predicted_topics = Column(Text)  # JSON array of topics
    technical_questions = Column(Text)  # JSON array of {question, difficulty, hint}
    hr_questions = Column(Text)  # JSON array of {question, sample_answer}
    model_answers = Column(Text)  # JSON dict of question -> answer
    
    # Daily preparation plan
    prep_plan = Column(Text)  # JSON with day-by-day plan
    
    # Tracking
    study_progress = Column(Text)  # JSON tracking which topics covered
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="interview_preps")
    
    def __repr__(self):
        return f"<InterviewPrep(id={self.id}, job_id={self.job_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "predicted_topics": json.loads(self.predicted_topics) if self.predicted_topics else [],
            "technical_questions": json.loads(self.technical_questions) if self.technical_questions else [],
            "hr_questions": json.loads(self.hr_questions) if self.hr_questions else [],
            "model_answers": json.loads(self.model_answers) if self.model_answers else {},
            "prep_plan": json.loads(self.prep_plan) if self.prep_plan else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def set_content(self, **kwargs):
        """Set content fields from dictionaries."""
        if "predicted_topics" in kwargs:
            self.predicted_topics = json.dumps(kwargs["predicted_topics"])
        if "technical_questions" in kwargs:
            self.technical_questions = json.dumps(kwargs["technical_questions"])
        if "hr_questions" in kwargs:
            self.hr_questions = json.dumps(kwargs["hr_questions"])
        if "model_answers" in kwargs:
            self.model_answers = json.dumps(kwargs["model_answers"])
        if "prep_plan" in kwargs:
            self.prep_plan = json.dumps(kwargs["prep_plan"])


class AuditLog(Base):
    """Timestamped audit log for all system actions."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # scraped, matched, approved, applied, etc.
    entity_type = Column(String(50))  # job, application, resume
    entity_id = Column(Integer)
    
    # User context (for future multi-user support)
    user_id = Column(Integer)
    
    # Details
    details = Column(Text)  # JSON with action-specific details
    status = Column(String(50))  # success, failed, warning
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for querying
    __table_args__ = (
        Index('idx_audit_action', 'action'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', entity={self.entity_type}#{self.entity_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": json.loads(self.details) if self.details else {},
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def log(cls, session, action: str, entity_type: str = None, entity_id: int = None,
            details: Dict = None, status: str = "success", error: str = None):
        """Convenience method to create audit log entries."""
        log_entry = cls(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details) if details else None,
            status=status,
            error_message=error,
        )
        session.add(log_entry)
        return log_entry


class UserPreferences(Base):
    """User preferences and settings."""
    
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Application settings
    auto_apply_enabled = Column(Boolean, default=False)
    min_match_score = Column(Float, default=70.0)
    daily_application_limit = Column(Integer, default=20)
    
    # Notification settings
    email_notifications = Column(Boolean, default=True)
    notification_email = Column(String(255))
    
    # Preferred platforms
    enabled_platforms = Column(Text)  # JSON array of platforms
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "auto_apply_enabled": self.auto_apply_enabled,
            "min_match_score": self.min_match_score,
            "daily_application_limit": self.daily_application_limit,
            "email_notifications": self.email_notifications,
            "enabled_platforms": json.loads(self.enabled_platforms) if self.enabled_platforms else [],
        }

