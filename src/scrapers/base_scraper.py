"""
Base Scraper Abstract Class

Defines the interface that all job platform scrapers must implement.
"""

import time
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from fake_useragent import UserAgent
import requests
from bs4 import BeautifulSoup

from ..database import Job, get_database, ScrapingSession


class BaseScraper(ABC):
    """Abstract base class for job platform scrapers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the scraper.
        
        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ua = UserAgent()
        self.db = get_database(config.get("database", {}).get("path", "data/jobs.db"))
        
        # Scraping settings
        self.request_delay = config.get("scraping", {}).get("request_delay", 2)
        self.max_jobs = config.get("scraping", {}).get("max_jobs_per_platform", 50)
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'linkedin', 'indeed')."""
        pass
    
    @abstractmethod
    def search_jobs(self, keywords: List[str], location: str = "", 
                    job_type: str = "", work_mode: str = "") -> List[Dict[str, Any]]:
        """Search for jobs on the platform.
        
        Args:
            keywords: List of search keywords
            location: Location filter
            job_type: Job type filter (full-time, internship, etc.)
            work_mode: Work mode filter (remote, hybrid, etc.)
            
        Returns:
            List of job dictionaries
        """
        pass
    
    @abstractmethod
    def parse_job_page(self, url: str) -> Dict[str, Any]:
        """Parse a job listing page for detailed information.
        
        Args:
            url: URL of the job listing
            
        Returns:
            Job details dictionary
        """
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """Get randomized headers for requests."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    
    def make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make an HTTP request with error handling and rate limiting.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests.get()
            
        Returns:
            Response object or None if failed
        """
        try:
            # Add random delay to avoid rate limiting
            time.sleep(self.request_delay + random.uniform(0, 1))
            
            headers = kwargs.pop("headers", self.get_headers())
            response = requests.get(url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object."""
        return BeautifulSoup(html, "html.parser")
    
    def save_job(self, job_data: Dict[str, Any]) -> Optional[Job]:
        """Save a job to the database.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Job object or None if duplicate
        """
        with self.db.get_session() as session:
            # Check if job already exists
            existing = session.query(Job).filter(Job.url == job_data.get("url")).first()
            if existing:
                self.logger.debug(f"Job already exists: {job_data.get('title')}")
                return None
            
            job = Job(
                title=job_data.get("title", ""),
                company=job_data.get("company", ""),
                location=job_data.get("location", ""),
                description=job_data.get("description", ""),
                requirements=job_data.get("requirements", ""),
                url=job_data.get("url", ""),
                platform=self.platform_name,
                job_type=job_data.get("job_type", ""),
                work_mode=job_data.get("work_mode", ""),
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                salary_currency=job_data.get("salary_currency"),
                posted_date=job_data.get("posted_date"),
                is_easy_apply=job_data.get("is_easy_apply", False),
            )
            session.add(job)
            self.logger.info(f"Saved job: {job.title} at {job.company}")
            return job
    
    def run(self, profile: Dict[str, Any]) -> int:
        """Run the scraper with the given user profile.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            Number of new jobs found
        """
        keywords = profile.get("keywords", [])
        preferences = profile.get("preferences", {})
        work_modes = preferences.get("work_mode", ["Remote"])
        job_types = preferences.get("employment_type", ["Full-time"])
        
        # Start scraping session
        with self.db.get_session() as session:
            scraping_session = ScrapingSession(
                platform=self.platform_name,
                status="running"
            )
            session.add(scraping_session)
            session.flush()
            session_id = scraping_session.id
        
        jobs_found = 0
        jobs_new = 0
        
        try:
            for keyword in keywords[:5]:  # Limit keywords to avoid too many requests
                for work_mode in work_modes:
                    self.logger.info(f"Searching for '{keyword}' ({work_mode})")
                    
                    jobs = self.search_jobs(
                        keywords=[keyword],
                        work_mode=work_mode,
                        job_type=job_types[0] if job_types else ""
                    )
                    
                    jobs_found += len(jobs)
                    
                    for job_data in jobs[:self.max_jobs]:
                        if self.save_job(job_data):
                            jobs_new += 1
                        
                        if jobs_new >= self.max_jobs:
                            break
                    
                    if jobs_new >= self.max_jobs:
                        break
                
                if jobs_new >= self.max_jobs:
                    break
            
            # Update session status
            with self.db.get_session() as session:
                scraping_session = session.query(ScrapingSession).get(session_id)
                if scraping_session:
                    scraping_session.status = "completed"
                    scraping_session.completed_at = datetime.utcnow()
                    scraping_session.jobs_found = jobs_found
                    scraping_session.jobs_new = jobs_new
                    
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            with self.db.get_session() as session:
                scraping_session = session.query(ScrapingSession).get(session_id)
                if scraping_session:
                    scraping_session.status = "failed"
                    scraping_session.error_message = str(e)
        
        return jobs_new
