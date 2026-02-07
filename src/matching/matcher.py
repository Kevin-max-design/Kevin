"""
Job Matching Engine

Matches scraped jobs against user profile based on skills, preferences, and requirements.
"""

import re
import json
from typing import List, Dict, Any, Set
from difflib import SequenceMatcher

from ..database import Job, get_database


class JobMatcher:
    """Matches jobs to user profile and calculates relevance scores."""
    
    # Common skill variations and synonyms
    SKILL_SYNONYMS = {
        "python": ["python3", "python 3", "py"],
        "machine learning": ["ml", "machine-learning", "machinelearning"],
        "deep learning": ["dl", "deep-learning", "deeplearning", "neural networks"],
        "natural language processing": ["nlp", "natural-language-processing"],
        "computer vision": ["cv", "image processing", "opencv"],
        "tensorflow": ["tf", "tensor flow", "tensor-flow"],
        "pytorch": ["torch", "py-torch"],
        "scikit-learn": ["sklearn", "scikit learn", "scikitlearn"],
        "data science": ["data-science", "datascience"],
        "data analysis": ["data-analysis", "dataanalysis"],
        "data engineering": ["data-engineering", "dataengineering"],
        "sql": ["mysql", "postgresql", "postgres", "sqlite", "oracle"],
        "aws": ["amazon web services", "amazon-web-services"],
        "gcp": ["google cloud", "google-cloud", "google cloud platform"],
        "azure": ["microsoft azure", "ms azure"],
    }
    
    # Role title patterns for matching
    ROLE_PATTERNS = {
        "ml engineer": [
            r"ml\s*engineer",
            r"machine\s*learning\s*engineer",
            r"ai\s*engineer",
            r"deep\s*learning\s*engineer",
        ],
        "data scientist": [
            r"data\s*scientist",
            r"senior\s*data\s*scientist",
            r"lead\s*data\s*scientist",
            r"research\s*scientist",
        ],
        "data analyst": [
            r"data\s*analyst",
            r"business\s*analyst",
            r"analytics\s*engineer",
            r"bi\s*analyst",
        ],
        "data engineer": [
            r"data\s*engineer",
            r"etl\s*engineer",
            r"data\s*platform",
        ],
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the matcher.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db = get_database(config.get("database", {}).get("path", "data/jobs.db"))
        
        # Matching weights from config
        matching_config = config.get("matching", {})
        weights = matching_config.get("weights", {})
        
        self.weight_skills = weights.get("skills", 0.40)
        self.weight_role = weights.get("role_title", 0.30)
        self.weight_work_mode = weights.get("work_mode", 0.15)
        self.weight_employment = weights.get("employment_type", 0.15)
        
        self.min_score = matching_config.get("min_score", 50)
    
    def match_job(self, job: Job, profile: Dict[str, Any]) -> float:
        """Calculate match score for a job against user profile.
        
        Args:
            job: Job database object
            profile: User profile dictionary
            
        Returns:
            Match score from 0 to 100
        """
        # Calculate individual scores
        skill_score = self._calculate_skill_score(job, profile)
        role_score = self._calculate_role_score(job, profile)
        work_mode_score = self._calculate_work_mode_score(job, profile)
        employment_score = self._calculate_employment_score(job, profile)
        
        # Calculate weighted total
        total_score = (
            skill_score * self.weight_skills +
            role_score * self.weight_role +
            work_mode_score * self.weight_work_mode +
            employment_score * self.weight_employment
        )
        
        return round(total_score, 2)
    
    def _calculate_skill_score(self, job: Job, profile: Dict[str, Any]) -> float:
        """Calculate skill match score.
        
        Args:
            job: Job object
            profile: User profile
            
        Returns:
            Score from 0 to 100
        """
        # Get user skills
        user_skills = set()
        skills_config = profile.get("skills", {})
        
        for category in ["programming", "domains", "tools", "cloud"]:
            for skill in skills_config.get(category, []):
                user_skills.add(skill.lower())
                # Add synonyms
                for base, synonyms in self.SKILL_SYNONYMS.items():
                    if skill.lower() == base or skill.lower() in synonyms:
                        user_skills.add(base)
                        user_skills.update(synonyms)
        
        # Get job text to search for skills
        job_text = f"{job.title} {job.description or ''} {job.requirements or ''}".lower()
        
        # Count matching skills
        matched = 0
        total_user_skills = len(skills_config.get("programming", [])) + \
                           len(skills_config.get("domains", [])) + \
                           len(skills_config.get("tools", []))
        
        for skill in user_skills:
            if skill in job_text:
                matched += 1
        
        if total_user_skills == 0:
            return 50  # Neutral score if no skills defined
        
        # Calculate percentage
        score = min((matched / total_user_skills) * 100, 100)
        return score
    
    def _calculate_role_score(self, job: Job, profile: Dict[str, Any]) -> float:
        """Calculate role title match score.
        
        Args:
            job: Job object
            profile: User profile
            
        Returns:
            Score from 0 to 100
        """
        target_roles = profile.get("preferences", {}).get("roles", [])
        job_title = job.title.lower()
        
        for target_role in target_roles:
            target_lower = target_role.lower()
            
            # Direct match
            if target_lower in job_title:
                return 100
            
            # Pattern matching
            for role_key, patterns in self.ROLE_PATTERNS.items():
                if role_key in target_lower:
                    for pattern in patterns:
                        if re.search(pattern, job_title, re.IGNORECASE):
                            return 100
            
            # Fuzzy match
            similarity = SequenceMatcher(None, target_lower, job_title).ratio()
            if similarity > 0.6:
                return similarity * 100
        
        # Check if it's at least in tech/data domain
        tech_keywords = ["engineer", "developer", "analyst", "scientist", "data", "ml", "ai"]
        for keyword in tech_keywords:
            if keyword in job_title:
                return 50
        
        return 20
    
    def _calculate_work_mode_score(self, job: Job, profile: Dict[str, Any]) -> float:
        """Calculate work mode preference score.
        
        Args:
            job: Job object
            profile: User profile
            
        Returns:
            Score from 0 to 100
        """
        preferred_modes = [m.lower() for m in profile.get("preferences", {}).get("work_mode", [])]
        job_mode = (job.work_mode or "").lower()
        job_location = (job.location or "").lower()
        
        # Check if job mode matches preference
        for mode in preferred_modes:
            if mode in job_mode or mode in job_location:
                return 100
            # Handle variations
            if mode in ["remote", "work from home", "wfh"] and any(
                m in job_location or m in job_mode 
                for m in ["remote", "work from home", "wfh", "anywhere"]
            ):
                return 100
        
        # If hybrid is acceptable and job is hybrid
        if "hybrid" in preferred_modes and "hybrid" in job_location:
            return 100
        
        # Neutral score if not specified
        if not job_mode and not any(mode in job_location for mode in ["remote", "hybrid", "onsite"]):
            return 70
        
        return 40
    
    def _calculate_employment_score(self, job: Job, profile: Dict[str, Any]) -> float:
        """Calculate employment type match score.
        
        Args:
            job: Job object
            profile: User profile
            
        Returns:
            Score from 0 to 100
        """
        preferred_types = [t.lower() for t in profile.get("preferences", {}).get("employment_type", [])]
        job_type = (job.job_type or "").lower()
        job_title = job.title.lower()
        
        # Check job type
        for pref_type in preferred_types:
            if pref_type in job_type:
                return 100
            # Check title for internship
            if pref_type == "internship" and "intern" in job_title:
                return 100
            if pref_type == "full-time" and ("full-time" in job_type or "fulltime" in job_type):
                return 100
        
        # Neutral if not specified
        if not job_type:
            return 70
        
        return 50
    
    def match_all_jobs(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Match all jobs in database against profile.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            List of jobs with match scores, sorted by score
        """
        matched_jobs = []
        
        with self.db.get_session() as session:
            jobs = session.query(Job).filter(Job.status == "new").all()
            
            for job in jobs:
                score = self.match_job(job, profile)
                
                if score >= self.min_score:
                    # Update job score in database
                    job.match_score = score
                    
                    matched_jobs.append({
                        "job": job.to_dict(),
                        "score": score,
                    })
        
        # Sort by score descending
        matched_jobs.sort(key=lambda x: x["score"], reverse=True)
        
        return matched_jobs
    
    def get_top_matches(self, profile: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """Get top matching jobs.
        
        Args:
            profile: User profile
            limit: Maximum number of jobs to return
            
        Returns:
            List of top matching jobs
        """
        all_matches = self.match_all_jobs(profile)
        return all_matches[:limit]
