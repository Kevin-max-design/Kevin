"""
AngelList/Wellfound Job Scraper

Scrapes job listings from Wellfound (formerly AngelList) for startup jobs.
"""

import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode

from .base_scraper import BaseScraper


class AngelListScraper(BaseScraper):
    """Scraper for Wellfound/AngelList job listings."""
    
    BASE_URL = "https://wellfound.com"
    SEARCH_URL = "https://wellfound.com/role"
    
    # Role mappings
    ROLE_MAPPINGS = {
        "data scientist": "data-scientist",
        "data analyst": "data-analyst",
        "ml engineer": "machine-learning-engineer",
        "machine learning": "machine-learning-engineer",
        "data engineer": "data-engineer",
    }
    
    @property
    def platform_name(self) -> str:
        return "angellist"
    
    def search_jobs(self, keywords: List[str], location: str = "",
                    job_type: str = "", work_mode: str = "") -> List[Dict[str, Any]]:
        """Search for jobs on Wellfound/AngelList.
        
        Args:
            keywords: Search keywords
            location: Location filter
            job_type: Job type filter
            work_mode: Work mode filter
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Map keywords to roles
        role_slug = "software-engineer"  # default
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for key, slug in self.ROLE_MAPPINGS.items():
                if key in keyword_lower:
                    role_slug = slug
                    break
        
        # Build search URL
        search_url = f"{self.SEARCH_URL}/{role_slug}"
        
        # Add remote filter
        if work_mode.lower() in ["remote", "work from home", "wfh"]:
            search_url += "?remote=true"
        
        self.logger.info(f"Searching Wellfound: {search_url}")
        
        response = self.make_request(search_url)
        if not response:
            return jobs
        
        soup = self.parse_html(response.text)
        
        # Find job cards
        job_cards = soup.find_all("div", class_=re.compile(r"styles_component"))
        
        if not job_cards:
            # Try to find jobs from script data
            script_data = soup.find("script", {"id": "__NEXT_DATA__"})
            if script_data:
                try:
                    data = json.loads(script_data.string)
                    page_props = data.get("props", {}).get("pageProps", {})
                    job_listings = page_props.get("seoLandingPageJobSearchResults", {}).get("startupJobPostings", [])
                    
                    for job in job_listings[:self.max_jobs]:
                        parsed_job = self._parse_job_data(job)
                        if parsed_job:
                            jobs.append(parsed_job)
                except json.JSONDecodeError:
                    pass
        
        for card in job_cards[:self.max_jobs]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Failed to parse Wellfound job card: {e}")
                continue
        
        self.logger.info(f"Found {len(jobs)} jobs on Wellfound")
        return jobs
    
    def _parse_job_data(self, job_data: Dict) -> Optional[Dict[str, Any]]:
        """Parse job data from JSON.
        
        Args:
            job_data: Job data dictionary from script
            
        Returns:
            Job dictionary or None
        """
        try:
            startup = job_data.get("startup", {})
            
            title = job_data.get("title", "")
            company = startup.get("name", "Unknown")
            location = job_data.get("locationNames", [""])[0] if job_data.get("locationNames") else ""
            
            job_url = f"{self.BASE_URL}/company/{startup.get('slug', '')}/jobs"
            
            # Check for remote
            work_mode = "remote" if job_data.get("remote", False) else ""
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "work_mode": work_mode,
                "is_easy_apply": True,  # Wellfound has easy apply
            }
        except Exception as e:
            self.logger.warning(f"Error parsing Wellfound job data: {e}")
            return None
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a Wellfound job card.
        
        Args:
            card: BeautifulSoup element for job card
            
        Returns:
            Job dictionary or None
        """
        try:
            # Find title
            title_elem = card.find("a", class_=re.compile(r"job-link")) or \
                        card.find("h4")
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            job_url = title_elem.get("href", "")
            
            if job_url and not job_url.startswith("http"):
                job_url = self.BASE_URL + job_url
            
            if not job_url:
                return None
            
            # Find company
            company_elem = card.find("h5") or card.find("span", class_=re.compile(r"company"))
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Find location
            location_elem = card.find("span", class_=re.compile(r"location"))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Check for remote
            work_mode = "remote" if "remote" in location.lower() else ""
            
            # Find salary
            salary_elem = card.find("span", class_=re.compile(r"salary"))
            salary = salary_elem.get_text(strip=True) if salary_elem else ""
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "work_mode": work_mode,
                "salary_text": salary,
                "is_easy_apply": True,
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing Wellfound job card: {e}")
            return None
    
    def parse_job_page(self, url: str) -> Dict[str, Any]:
        """Parse a full Wellfound job listing page.
        
        Args:
            url: Job listing URL
            
        Returns:
            Detailed job information
        """
        response = self.make_request(url)
        if not response:
            return {}
        
        soup = self.parse_html(response.text)
        
        job_data = {
            "url": url,
        }
        
        # Find job description
        description_elem = soup.find("div", class_=re.compile(r"job-description")) or \
                          soup.find("div", class_=re.compile(r"content"))
        if description_elem:
            job_data["description"] = description_elem.get_text(separator="\n", strip=True)
        
        return job_data
