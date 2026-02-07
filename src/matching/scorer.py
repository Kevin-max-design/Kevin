"""
Job Scoring and Ranking

Additional scoring utilities for ranking and prioritizing jobs.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..database import Job, get_database


class JobScorer:
    """Additional scoring utilities for job prioritization."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize scorer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db = get_database(config.get("database", {}).get("path", "data/jobs.db"))
    
    def calculate_priority_score(self, job: Job, match_score: float) -> float:
        """Calculate overall priority score including recency and other factors.
        
        Args:
            job: Job object
            match_score: Base match score from JobMatcher
            
        Returns:
            Priority score from 0 to 100
        """
        # Start with match score (weighted 70%)
        priority = match_score * 0.7
        
        # Add recency bonus (up to 15%)
        recency_bonus = self._calculate_recency_bonus(job)
        priority += recency_bonus * 0.15
        
        # Add easy apply bonus (10%)
        if job.is_easy_apply:
            priority += 10
        
        # Company preference bonus (5%)
        # This could be enhanced with company ratings, culture data, etc.
        priority += 5  # Default bonus
        
        return min(priority, 100)
    
    def _calculate_recency_bonus(self, job: Job) -> float:
        """Calculate bonus based on how recently the job was posted.
        
        Args:
            job: Job object
            
        Returns:
            Recency bonus from 0 to 100
        """
        if not job.posted_date:
            return 50  # Neutral if unknown
        
        now = datetime.utcnow()
        age = now - job.posted_date
        
        if age < timedelta(days=1):
            return 100  # Posted today
        elif age < timedelta(days=3):
            return 80  # Posted in last 3 days
        elif age < timedelta(days=7):
            return 60  # Posted in last week
        elif age < timedelta(days=14):
            return 40  # Posted in last 2 weeks
        else:
            return 20  # Older than 2 weeks
    
    def rank_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank jobs by priority score.
        
        Args:
            jobs: List of job dictionaries with 'job' and 'score' keys
            
        Returns:
            Sorted list with added 'priority' key
        """
        with self.db.get_session() as session:
            for job_data in jobs:
                job_id = job_data["job"]["id"]
                job = session.query(Job).get(job_id)
                
                if job:
                    priority = self.calculate_priority_score(job, job_data["score"])
                    job_data["priority"] = priority
        
        # Sort by priority
        jobs.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        return jobs
    
    def filter_applied_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out jobs that have already been applied to.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Filtered list
        """
        return [j for j in jobs if j["job"].get("status") == "new"]
    
    def get_application_queue(self, jobs: List[Dict[str, Any]], 
                              daily_limit: int = 20) -> List[Dict[str, Any]]:
        """Get queue of jobs to apply to, respecting daily limits.
        
        Args:
            jobs: List of ranked job dictionaries
            daily_limit: Maximum applications per day
            
        Returns:
            Jobs to apply to today
        """
        # Filter and limit
        filtered = self.filter_applied_jobs(jobs)
        return filtered[:daily_limit]
