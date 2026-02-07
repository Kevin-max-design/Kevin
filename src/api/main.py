"""
FastAPI Backend for Job Application Agent Dashboard

Provides REST API for monitoring and controlling the agent.
Enhanced with approval workflow, tracking, and interview prep endpoints.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import yaml
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, and_

from ..database import Job, Application, AuditLog, get_database
from ..scrapers import get_all_scrapers
from ..matching import JobMatcher, JobScorer
from ..applicator import ApplicationManager


# Load config
def load_config() -> Dict[str, Any]:
    try:
        with open("config/config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

def load_profile() -> Dict[str, Any]:
    try:
        with open("data/profile.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


# API Models
class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str]
    description: Optional[str]
    url: str
    platform: str
    job_type: Optional[str]
    work_mode: Optional[str]
    match_score: Optional[float]
    semantic_score: Optional[float]
    matched_skills: List[str]
    missing_skills: List[str]
    status: str
    is_approved: bool
    is_easy_apply: bool
    posted_date: Optional[datetime]
    scraped_at: Optional[datetime]
    applied_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    status: str
    application_method: Optional[str]
    applied_at: Optional[datetime]
    response_received: bool
    job_title: Optional[str]
    company: Optional[str]

class StatsResponse(BaseModel):
    status_counts: Dict[str, int]
    recent_applied: int
    total_applied: int
    interview_count: int
    offer_count: int
    interview_rate: float
    offer_rate: float
    platform_counts: Dict[str, int]
    average_match_score: float
    period_days: int = 30

class ApproveRequest(BaseModel):
    notes: Optional[str] = None

class RejectRequest(BaseModel):
    reason: Optional[str] = None

class ScrapeRequest(BaseModel):
    platforms: Optional[List[str]] = None

class ActivityResponse(BaseModel):
    id: int
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    details: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    job_title: Optional[str] = None
    company: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Job Application Agent",
    description="AI-powered job application automation with human-in-the-loop approval",
    version="2.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper functions
def get_db():
    config = load_config()
    return get_database(config.get("database", {}).get("path", "data/jobs.db"))


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "running", "message": "Job Application Agent API v2.0"}


# ==================== Stats Endpoints ====================

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(days: int = Query(30, le=365)):
    """Get comprehensive application statistics."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    with db.get_session() as session:
        # Status counts
        status_counts = dict(session.query(
            Job.status,
            func.count(Job.id)
        ).group_by(Job.status).all())
        
        # Platform counts
        platform_counts = dict(session.query(
            Job.platform,
            func.count(Job.id)
        ).group_by(Job.platform).all())
        
        # Applied in period
        recent_applied = session.query(func.count(Job.id)).filter(
            and_(
                Job.status == "applied",
                Job.applied_at >= cutoff,
            )
        ).scalar() or 0
        
        # Total applied
        total_applied = session.query(func.count(Job.id)).filter(
            Job.status.in_(["applied", "interview", "offer", "rejected"])
        ).scalar() or 0
        
        # Interview and offer counts
        interview_count = session.query(func.count(Job.id)).filter(
            Job.status.in_(["interview", "offer"])
        ).scalar() or 0
        
        offer_count = session.query(func.count(Job.id)).filter(
            Job.status == "offer"
        ).scalar() or 0
        
        # Average match score
        avg_score = session.query(
            func.avg(Job.match_score)
        ).filter(Job.match_score > 0).scalar() or 0
        
        return {
            "status_counts": status_counts,
            "recent_applied": recent_applied,
            "total_applied": total_applied,
            "interview_count": interview_count,
            "offer_count": offer_count,
            "interview_rate": (interview_count / total_applied * 100) if total_applied > 0 else 0,
            "offer_rate": (offer_count / total_applied * 100) if total_applied > 0 else 0,
            "platform_counts": platform_counts,
            "average_match_score": round(avg_score, 1),
            "period_days": days,
        }


# ==================== Jobs Endpoints ====================

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_score: Optional[float] = Query(None, description="Minimum match score"),
    limit: int = Query(50, le=200, description="Maximum jobs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get list of jobs with filtering."""
    db = get_db()
    
    with db.get_session() as session:
        query = session.query(Job)
        
        if status:
            query = query.filter(Job.status == status)
        if platform:
            query = query.filter(Job.platform == platform)
        if min_score is not None:
            query = query.filter(Job.match_score >= min_score)
        
        query = query.order_by(Job.updated_at.desc())
        jobs = query.offset(offset).limit(limit).all()
        
        return [job.to_dict() for job in jobs]


@app.get("/api/jobs/pending", response_model=List[JobResponse])
async def get_pending_approvals(limit: int = Query(50, le=100)):
    """Get jobs pending user approval."""
    db = get_db()
    
    with db.get_session() as session:
        jobs = session.query(Job).filter(
            and_(
                Job.status == "matched",
                Job.is_approved == False,
                Job.match_score > 0,
            )
        ).order_by(Job.match_score.desc()).limit(limit).all()
        
        return [job.to_dict() for job in jobs]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int):
    """Get a specific job."""
    db = get_db()
    
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.to_dict()


@app.post("/api/jobs/{job_id}/approve")
async def approve_job(job_id: int, request: ApproveRequest = None):
    """Approve a job for application."""
    db = get_db()
    
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        old_status = job.status
        job.status = "approved"
        job.is_approved = True
        job.approved_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        if request and request.notes:
            job.approval_notes = request.notes
        
        # Log action
        AuditLog.log(
            session,
            action="status_change",
            entity_type="job",
            entity_id=job_id,
            details={"old_status": old_status, "new_status": "approved", "notes": request.notes if request else None},
        )
        
        session.commit()
        return {"message": "Job approved", "job_id": job_id}


@app.post("/api/jobs/{job_id}/reject")
async def reject_job(job_id: int, request: RejectRequest = None):
    """Reject a job from the approval queue."""
    db = get_db()
    
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        old_status = job.status
        job.status = "rejected"
        job.is_approved = False
        job.updated_at = datetime.utcnow()
        
        if request and request.reason:
            job.approval_notes = request.reason
        
        # Log action
        AuditLog.log(
            session,
            action="status_change",
            entity_type="job",
            entity_id=job_id,
            details={"old_status": old_status, "new_status": "rejected", "reason": request.reason if request else None},
        )
        
        session.commit()
        return {"message": "Job rejected", "job_id": job_id}


@app.post("/api/jobs/{job_id}/apply")
async def apply_to_job(job_id: int, background_tasks: BackgroundTasks):
    """Apply to a specific job."""
    config = load_config()
    profile = load_profile()
    db = get_db()
    
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.is_approved:
            raise HTTPException(status_code=400, detail="Job not approved. Approve it first.")
    
    manager = ApplicationManager(config)
    
    # Prepare application materials first
    materials = manager.prepare_application(job_id, profile)
    
    if "error" in materials:
        raise HTTPException(status_code=404, detail=materials["error"])
    
    def run_apply():
        with db.get_session() as session:
            manager.apply_single(job_id, profile)
            
            job = session.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "applied"
                job.applied_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                
                AuditLog.log(
                    session,
                    action="application_attempt",
                    entity_type="job",
                    entity_id=job_id,
                    details={"method": "automated"},
                    status="success",
                )
                session.commit()
    
    background_tasks.add_task(run_apply)
    
    return {
        "success": True,
        "message": "Application started",
        "job_id": job_id,
    }


# ==================== Cover Letter & Interview Prep ====================

@app.get("/api/jobs/{job_id}/cover-letter")
async def preview_cover_letter(job_id: int):
    """Preview cover letter for a job."""
    config = load_config()
    profile = load_profile()
    
    manager = ApplicationManager(config)
    materials = manager.prepare_application(job_id, profile)
    
    if "error" in materials:
        raise HTTPException(status_code=404, detail=materials["error"])
    
    return {
        "job": materials["job"],
        "cover_letter": materials["cover_letter"],
        "match_score": materials["match_score"],
    }


@app.post("/api/jobs/{job_id}/interview-prep")
async def generate_interview_prep(job_id: int):
    """Generate interview preparation materials for a job."""
    config = load_config()
    profile = load_profile()
    db = get_db()
    
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job.to_dict()
    
    try:
        from ..interview import InterviewPrepGenerator
        
        generator = InterviewPrepGenerator(config)
        prep = generator.generate_prep(job_data, profile)
        
        return prep
        
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Interview prep module not available"
        )


# ==================== Scraping & Matching ====================

@app.post("/api/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    request: ScrapeRequest = None,
):
    """Trigger job scraping."""
    config = load_config()
    profile = load_profile()
    
    def run_scrape():
        scrapers = get_all_scrapers(config)
        total_new = 0
        
        for scraper in scrapers:
            if request and request.platforms:
                if scraper.platform_name not in request.platforms:
                    continue
            
            try:
                new_jobs = scraper.run(profile)
                total_new += new_jobs
            except Exception as e:
                print(f"Scraper {scraper.platform_name} failed: {e}")
    
    background_tasks.add_task(run_scrape)
    
    return {"message": "Scraping started", "platforms": request.platforms if request else "all"}


@app.post("/api/match")
async def match_jobs():
    """Run job matching on all new jobs."""
    config = load_config()
    profile = load_profile()
    db = get_db()
    
    matcher = JobMatcher(config)
    matches = matcher.match_all_jobs(profile)
    
    # Update job statuses
    matched_count = 0
    with db.get_session() as session:
        for match in matches:
            job = session.query(Job).filter(Job.id == match["job"]["id"]).first()
            if job and job.status == "new":
                job.status = "matched"
                job.matched_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                matched_count += 1
        session.commit()
    
    return {
        "message": "Matching complete",
        "matched": matched_count,
        "total_processed": len(matches),
    }


# ==================== Activity & Export ====================

@app.get("/api/activity", response_model=List[ActivityResponse])
async def get_activity(limit: int = Query(20, le=100)):
    """Get recent activity feed."""
    db = get_db()
    
    with db.get_session() as session:
        logs = session.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()
        
        activities = []
        for log in logs:
            activity = {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "status": log.status,
                "created_at": log.created_at,
            }
            
            # Add job details if available
            if log.entity_type == "job" and log.entity_id:
                job = session.query(Job).filter(Job.id == log.entity_id).first()
                if job:
                    activity["job_title"] = job.title
                    activity["company"] = job.company
            
            activities.append(activity)
        
        return activities


@app.get("/api/export")
async def export_data(
    format: str = Query("json", enum=["json", "csv"]),
    status: Optional[str] = None,
):
    """Export job data."""
    db = get_db()
    
    with db.get_session() as session:
        query = session.query(Job)
        
        if status:
            query = query.filter(Job.status == status)
        
        jobs = query.order_by(Job.updated_at.desc()).all()
        
        if format == "json":
            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "total_jobs": len(jobs),
                "jobs": [job.to_dict() for job in jobs],
            }
            return Response(
                content=json.dumps(data, default=str, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=jobs_export.json"}
            )
        
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            fields = ["id", "title", "company", "location", "platform", 
                     "match_score", "status", "url", "applied_at"]
            
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            
            for job in jobs:
                writer.writerow(job.to_dict())
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=jobs_export.csv"}
            )


# ==================== Applications ====================

@app.get("/api/applications", response_model=List[ApplicationResponse])
async def get_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=200),
):
    """Get list of applications."""
    db = get_db()
    
    with db.get_session() as session:
        query = session.query(Application).join(Job)
        
        if status:
            query = query.filter(Application.status == status)
        
        query = query.order_by(Application.applied_at.desc())
        applications = query.limit(limit).all()
        
        return [
            {
                **app.to_dict(),
                "job_title": app.job.title if app.job else None,
                "company": app.job.company if app.job else None,
            }
            for app in applications
        ]
