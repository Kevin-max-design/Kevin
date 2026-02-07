"""
Application Tracker - Comprehensive job application status tracking.

Tracks all applications with status history, timestamps, and analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, or_

from ..database import Database, Job, Application, AuditLog


class ApplicationTracker:
    """
    Track and manage job applications with full history.
    
    Features:
    - Status tracking with timestamps
    - Application analytics
    - Activity logging
    - Dashboard data generation
    """
    
    # Status workflow
    STATUS_FLOW = {
        "new": ["matched", "rejected"],
        "matched": ["approved", "rejected"],
        "approved": ["applied", "rejected"],
        "applied": ["interview", "rejected", "offer"],
        "interview": ["offer", "rejected"],
        "offer": ["accepted", "rejected"],
        "rejected": [],
        "accepted": [],
    }
    
    def __init__(self, db: Database):
        """
        Initialize tracker.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def update_status(
        self,
        job_id: int,
        new_status: str,
        notes: str = None,
    ) -> bool:
        """
        Update job application status.
        
        Args:
            job_id: Job ID to update
            new_status: New status value
            notes: Optional notes for status change
            
        Returns:
            True if successful
        """
        with self.db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            
            if not job:
                self.logger.error(f"Job {job_id} not found")
                return False
            
            old_status = job.status
            
            # Validate status transition
            if new_status not in self.STATUS_FLOW.get(old_status, [new_status]):
                self.logger.warning(f"Invalid status transition: {old_status} -> {new_status}")
            
            # Update status
            job.status = new_status
            job.updated_at = datetime.utcnow()
            
            # Update specific timestamp
            if new_status == "matched":
                job.matched_at = datetime.utcnow()
            elif new_status == "approved":
                job.approved_at = datetime.utcnow()
                job.is_approved = True
            elif new_status == "applied":
                job.applied_at = datetime.utcnow()
            elif new_status == "rejected":
                job.is_approved = False
            
            # Add approval notes
            if notes:
                job.approval_notes = notes
            
            # Create audit log
            AuditLog.log(
                session,
                action="status_change",
                entity_type="job",
                entity_id=job_id,
                details={
                    "old_status": old_status,
                    "new_status": new_status,
                    "notes": notes,
                },
            )
            
            session.commit()
            self.logger.info(f"Job {job_id} status: {old_status} -> {new_status}")
            return True
    
    def get_job_history(self, job_id: int) -> List[Dict[str, Any]]:
        """
        Get status history for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of status change events
        """
        with self.db.get_session() as session:
            logs = session.query(AuditLog).filter(
                and_(
                    AuditLog.entity_type == "job",
                    AuditLog.entity_id == job_id,
                )
            ).order_by(AuditLog.created_at.desc()).all()
            
            return [log.to_dict() for log in logs]
    
    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get application statistics.
        
        Args:
            days: Number of days to include
            
        Returns:
            Statistics dictionary
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.db.get_session() as session:
            # Job counts by status
            status_counts = session.query(
                Job.status,
                func.count(Job.id)
            ).group_by(Job.status).all()
            
            # Applications in period
            recent_applied = session.query(func.count(Job.id)).filter(
                and_(
                    Job.status == "applied",
                    Job.applied_at >= cutoff,
                )
            ).scalar() or 0
            
            # Interview rate
            total_applied = session.query(func.count(Job.id)).filter(
                Job.status.in_(["applied", "interview", "offer", "rejected"])
            ).scalar() or 0
            
            interview_count = session.query(func.count(Job.id)).filter(
                Job.status.in_(["interview", "offer"])
            ).scalar() or 0
            
            # Offers
            offer_count = session.query(func.count(Job.id)).filter(
                Job.status == "offer"
            ).scalar() or 0
            
            # Jobs by platform
            platform_counts = session.query(
                Job.platform,
                func.count(Job.id)
            ).group_by(Job.platform).all()
            
            # Average match score
            avg_score = session.query(
                func.avg(Job.match_score)
            ).filter(Job.match_score > 0).scalar() or 0
            
            return {
                "status_counts": dict(status_counts),
                "recent_applied": recent_applied,
                "total_applied": total_applied,
                "interview_count": interview_count,
                "offer_count": offer_count,
                "interview_rate": (interview_count / total_applied * 100) if total_applied > 0 else 0,
                "offer_rate": (offer_count / total_applied * 100) if total_applied > 0 else 0,
                "platform_counts": dict(platform_counts),
                "average_match_score": round(avg_score, 1),
                "period_days": days,
            }
    
    def get_pending_approvals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get jobs pending user approval.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of jobs needing approval
        """
        with self.db.get_session() as session:
            jobs = session.query(Job).filter(
                and_(
                    Job.status == "matched",
                    Job.is_approved == False,
                    Job.match_score > 0,
                )
            ).order_by(Job.match_score.desc()).limit(limit).all()
            
            return [job.to_dict() for job in jobs]
    
    def get_applied_today(self) -> int:
        """Get count of applications submitted today."""
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        with self.db.get_session() as session:
            count = session.query(func.count(Job.id)).filter(
                and_(
                    Job.status == "applied",
                    Job.applied_at >= today_start,
                )
            ).scalar() or 0
            
            return count
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent application activity.
        
        Args:
            limit: Maximum entries to return
            
        Returns:
            List of recent activities
        """
        with self.db.get_session() as session:
            logs = session.query(AuditLog).order_by(
                AuditLog.created_at.desc()
            ).limit(limit).all()
            
            activities = []
            for log in logs:
                activity = log.to_dict()
                
                # Add entity details if available
                if log.entity_type == "job" and log.entity_id:
                    job = session.query(Job).filter(Job.id == log.entity_id).first()
                    if job:
                        activity["job_title"] = job.title
                        activity["company"] = job.company
                
                activities.append(activity)
            
            return activities
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive data for dashboard display.
        
        Returns:
            Dashboard data dictionary
        """
        stats = self.get_stats(30)
        
        return {
            "stats": stats,
            "pending_approvals": len(self.get_pending_approvals(100)),
            "applied_today": self.get_applied_today(),
            "recent_activity": self.get_recent_activity(10),
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def search_applications(
        self,
        query: str = None,
        status: str = None,
        platform: str = None,
        min_score: float = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search applications with filters.
        
        Args:
            query: Search query for title/company
            status: Filter by status
            platform: Filter by platform
            min_score: Minimum match score
            limit: Maximum results
            
        Returns:
            List of matching jobs
        """
        with self.db.get_session() as session:
            q = session.query(Job)
            
            if query:
                search_term = f"%{query}%"
                q = q.filter(
                    or_(
                        Job.title.ilike(search_term),
                        Job.company.ilike(search_term),
                    )
                )
            
            if status:
                q = q.filter(Job.status == status)
            
            if platform:
                q = q.filter(Job.platform == platform)
            
            if min_score is not None:
                q = q.filter(Job.match_score >= min_score)
            
            jobs = q.order_by(Job.updated_at.desc()).limit(limit).all()
            
            return [job.to_dict() for job in jobs]
    
    def log_action(
        self,
        action: str,
        entity_type: str = None,
        entity_id: int = None,
        details: Dict = None,
        status: str = "success",
        error: str = None,
    ):
        """
        Log an action for audit trail.
        
        Args:
            action: Action name
            entity_type: Type of entity (job, application, etc.)
            entity_id: Entity ID
            details: Additional details
            status: Action status
            error: Error message if failed
        """
        with self.db.get_session() as session:
            AuditLog.log(
                session,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                status=status,
                error=error,
            )
            session.commit()
