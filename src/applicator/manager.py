"""
Application Manager

Orchestrates the job application process.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..database import Job, Application, get_database
from ..matching import JobMatcher, JobScorer
from ..llm import CoverLetterGenerator
from .form_filler import FormFiller


class ApplicationManager:
    """Manages the job application workflow."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize application manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db = get_database(config.get("database", {}).get("path", "data/jobs.db"))
        
        self.matcher = JobMatcher(config)
        self.scorer = JobScorer(config)
        self.form_filler = FormFiller(config)
        self.cover_letter_gen = CoverLetterGenerator(config)
        
        self.logger = logging.getLogger(__name__)
        
        # Application settings
        app_config = config.get("application", {})
        self.auto_apply_min_score = app_config.get("auto_apply_min_score", 70)
        self.daily_limit = app_config.get("daily_limit", 20)
    
    def get_pending_applications(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get jobs ready for application.
        
        Args:
            profile: User profile
            
        Returns:
            List of job dictionaries with scores
        """
        # Get matched jobs
        matches = self.matcher.match_all_jobs(profile)
        
        # Filter by auto-apply score
        qualified = [m for m in matches if m["score"] >= self.auto_apply_min_score]
        
        # Rank by priority
        ranked = self.scorer.rank_jobs(qualified)
        
        # Get application queue
        queue = self.scorer.get_application_queue(ranked, self.daily_limit)
        
        return queue
    
    def apply_batch(self, profile: Dict[str, Any], limit: int = None) -> Dict[str, int]:
        """Apply to multiple jobs.
        
        Args:
            profile: User profile
            limit: Maximum applications (defaults to daily limit)
            
        Returns:
            Stats dictionary with success/failure counts
        """
        limit = limit or self.daily_limit
        
        # Check today's applications
        today_count = self._get_today_application_count()
        remaining = max(0, limit - today_count)
        
        if remaining == 0:
            self.logger.info("Daily application limit reached")
            return {"submitted": 0, "failed": 0, "limit_reached": True}
        
        # Get pending jobs
        pending = self.get_pending_applications(profile)[:remaining]
        
        stats = {"submitted": 0, "failed": 0, "skipped": 0}
        
        for job_data in pending:
            job_id = job_data["job"]["id"]
            
            with self.db.get_session() as session:
                job = session.query(Job).get(job_id)
                
                if not job or job.status != "new":
                    stats["skipped"] += 1
                    continue
                
                # Apply
                success = self.form_filler.apply_to_job(job, profile)
                
                if success:
                    stats["submitted"] += 1
                else:
                    stats["failed"] += 1
        
        self.logger.info(f"Batch application complete: {stats}")
        return stats
    
    def apply_single(self, job_id: int, profile: Dict[str, Any]) -> bool:
        """Apply to a single job.
        
        Args:
            job_id: Job database ID
            profile: User profile
            
        Returns:
            True if successful
        """
        with self.db.get_session() as session:
            job = session.query(Job).get(job_id)
            
            if not job:
                self.logger.error(f"Job {job_id} not found")
                return False
            
            return self.form_filler.apply_to_job(job, profile)
    
    def prepare_application(self, job_id: int, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare application materials without submitting.
        
        Args:
            job_id: Job database ID
            profile: User profile
            
        Returns:
            Dictionary with prepared materials
        """
        with self.db.get_session() as session:
            job = session.query(Job).get(job_id)
            
            if not job:
                return {"error": "Job not found"}
            
            job_dict = job.to_dict()
            job_dict["description"] = job.description
            
            # Generate cover letter
            cover_letter = self.cover_letter_gen.generate(job_dict, profile)
            
            # Calculate match score
            score = self.matcher.match_job(job, profile)
            
            return {
                "job": job_dict,
                "cover_letter": cover_letter,
                "match_score": score,
                "status": "prepared",
            }
    
    def _get_today_application_count(self) -> int:
        """Get number of applications submitted today."""
        today = datetime.utcnow().date()
        
        with self.db.get_session() as session:
            count = session.query(Application).filter(
                Application.applied_at >= datetime.combine(today, datetime.min.time())
            ).count()
            
            return count
    
    def get_application_stats(self) -> Dict[str, Any]:
        """Get application statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.db.get_session() as session:
            total_jobs = session.query(Job).count()
            applied = session.query(Job).filter(Job.status == "applied").count()
            pending = session.query(Job).filter(Job.status == "new").count()
            
            today = datetime.utcnow().date()
            today_apps = session.query(Application).filter(
                Application.applied_at >= datetime.combine(today, datetime.min.time())
            ).count()
            
            week_start = today - timedelta(days=today.weekday())
            week_apps = session.query(Application).filter(
                Application.applied_at >= datetime.combine(week_start, datetime.min.time())
            ).count()
            
            return {
                "total_jobs": total_jobs,
                "applied": applied,
                "pending": pending,
                "today_applications": today_apps,
                "week_applications": week_apps,
                "remaining_today": max(0, self.daily_limit - today_apps),
            }
