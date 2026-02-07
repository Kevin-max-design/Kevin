"""
LinkedIn Job Scraper

Scrapes job listings from LinkedIn.
Note: LinkedIn requires authentication for full functionality.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode, quote_plus

from .base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job listings."""
    
    BASE_URL = "https://www.linkedin.com"
    SEARCH_URL = "https://www.linkedin.com/jobs/search"
    
    # Work type filters
    WORK_TYPE_FILTERS = {
        "remote": "2",
        "hybrid": "3",
        "onsite": "1",
    }
    
    # Job type filters
    JOB_TYPE_FILTERS = {
        "full-time": "F",
        "part-time": "P",
        "contract": "C",
        "internship": "I",
    }
    
    @property
    def platform_name(self) -> str:
        return "linkedin"
    
    def search_jobs(self, keywords: List[str], location: str = "",
                    job_type: str = "", work_mode: str = "") -> List[Dict[str, Any]]:
        """Search for jobs on LinkedIn (public listings).
        
        Args:
            keywords: Search keywords
            location: Location filter
            job_type: Job type filter
            work_mode: Work mode filter (remote, hybrid, onsite)
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        query = " ".join(keywords)
        
        # Build search parameters
        params = {
            "keywords": query,
            "location": location if location else "Worldwide",
            "f_TPR": "r604800",  # Last 7 days
            "position": 1,
            "pageNum": 0,
        }
        
        # Add work type filter
        if work_mode.lower() in self.WORK_TYPE_FILTERS:
            params["f_WT"] = self.WORK_TYPE_FILTERS[work_mode.lower()]
        elif work_mode.lower() in ["remote", "work from home", "wfh"]:
            params["f_WT"] = self.WORK_TYPE_FILTERS["remote"]
        
        # Add job type filter
        if job_type.lower() in self.JOB_TYPE_FILTERS:
            params["f_JT"] = self.JOB_TYPE_FILTERS[job_type.lower()]
        
        search_url = f"{self.SEARCH_URL}?{urlencode(params)}"
        self.logger.info(f"Searching LinkedIn: {search_url}")
        
        response = self.make_request(search_url)
        if not response:
            return jobs
        
        soup = self.parse_html(response.text)
        
        # Find job cards
        job_cards = soup.find_all("div", class_=re.compile(r"base-card|job-search-card"))
        
        if not job_cards:
            job_cards = soup.find_all("li", class_=re.compile(r"jobs-search-results__list-item"))
        
        for card in job_cards[:self.max_jobs]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Failed to parse job card: {e}")
                continue
        
        self.logger.info(f"Found {len(jobs)} jobs on LinkedIn")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a LinkedIn job card.
        
        Args:
            card: BeautifulSoup element for job card
            
        Returns:
            Job dictionary or None
        """
        try:
            # Find title
            title_elem = card.find("h3", class_=re.compile(r"base-search-card__title")) or \
                        card.find("a", class_=re.compile(r"base-card__full-link"))
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Find job URL
            link = card.find("a", class_=re.compile(r"base-card__full-link"))
            if link and link.get("href"):
                job_url = link["href"].split("?")[0]  # Remove tracking params
            else:
                return None
            
            # Find company
            company_elem = card.find("h4", class_=re.compile(r"base-search-card__subtitle")) or \
                          card.find("a", class_=re.compile(r"hidden-nested-link"))
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Find location
            location_elem = card.find("span", class_=re.compile(r"job-search-card__location"))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Check for remote
            work_mode = ""
            if "remote" in location.lower():
                work_mode = "remote"
            elif "hybrid" in location.lower():
                work_mode = "hybrid"
            
            # Find posted date
            date_elem = card.find("time", class_=re.compile(r"job-search-card__listdate"))
            posted_date = None
            if date_elem and date_elem.get("datetime"):
                try:
                    posted_date = datetime.fromisoformat(date_elem["datetime"].replace("Z", "+00:00"))
                except:
                    pass
            
            # Check for easy apply
            easy_apply = bool(card.find("span", string=re.compile(r"Easy Apply", re.I)))
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "work_mode": work_mode,
                "posted_date": posted_date,
                "is_easy_apply": easy_apply,
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing LinkedIn job card: {e}")
            return None
    
    def parse_job_page(self, url: str) -> Dict[str, Any]:
        """Parse a full LinkedIn job listing page.
        
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
        description_elem = soup.find("div", class_=re.compile(r"description__text")) or \
                          soup.find("div", class_=re.compile(r"show-more-less-html__markup"))
        if description_elem:
            job_data["description"] = description_elem.get_text(separator="\n", strip=True)
        
        # Find job criteria
        criteria_list = soup.find_all("li", class_=re.compile(r"description__job-criteria-item"))
        for criteria in criteria_list:
            header = criteria.find("h3")
            value = criteria.find("span")
            if header and value:
                key = header.get_text(strip=True).lower()
                val = value.get_text(strip=True)
                if "type" in key:
                    job_data["job_type"] = val
                elif "level" in key:
                    job_data["seniority_level"] = val
        
        return job_data
