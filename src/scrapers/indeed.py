"""
Indeed Job Scraper

Scrapes job listings from Indeed.com
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus

from .base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper for Indeed job listings."""
    
    BASE_URL = "https://www.indeed.com"
    SEARCH_URL = "https://www.indeed.com/jobs"
    
    @property
    def platform_name(self) -> str:
        return "indeed"
    
    def search_jobs(self, keywords: List[str], location: str = "",
                    job_type: str = "", work_mode: str = "") -> List[Dict[str, Any]]:
        """Search for jobs on Indeed.
        
        Args:
            keywords: Search keywords
            location: Location filter
            job_type: Job type (fulltime, parttime, internship, etc.)
            work_mode: Work mode (remote, etc.)
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        query = " ".join(keywords)
        
        # Build search parameters
        params = {
            "q": query,
            "l": location if location else "",
            "sort": "date",  # Sort by date
            "fromage": 14,   # Last 14 days
        }
        
        # Add job type filter
        if job_type.lower() == "internship":
            params["jt"] = "internship"
        elif job_type.lower() == "full-time":
            params["jt"] = "fulltime"
        
        # Add remote filter
        if work_mode.lower() in ["remote", "work from home", "wfh"]:
            params["remotejob"] = "1"
        
        search_url = f"{self.SEARCH_URL}?{urlencode(params)}"
        self.logger.info(f"Searching Indeed: {search_url}")
        
        response = self.make_request(search_url)
        if not response:
            return jobs
        
        soup = self.parse_html(response.text)
        
        # Find job cards
        job_cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobsearch-ResultsList"))
        
        # Also try alternative selectors
        if not job_cards:
            job_cards = soup.find_all("div", {"data-jk": True})
        
        if not job_cards:
            job_cards = soup.find_all("a", class_=re.compile(r"jcs-JobTitle"))
        
        for card in job_cards[:self.max_jobs]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Failed to parse job card: {e}")
                continue
        
        self.logger.info(f"Found {len(jobs)} jobs on Indeed")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a job card element.
        
        Args:
            card: BeautifulSoup element for job card
            
        Returns:
            Job dictionary or None
        """
        try:
            # Find title
            title_elem = card.find("h2", class_=re.compile(r"jobTitle")) or \
                        card.find("a", class_=re.compile(r"jcs-JobTitle"))
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Find job URL
            link = title_elem.find("a") if title_elem.name != "a" else title_elem
            if link and link.get("href"):
                job_id = link.get("data-jk") or card.get("data-jk", "")
                if job_id:
                    job_url = f"{self.BASE_URL}/viewjob?jk={job_id}"
                else:
                    job_url = self.BASE_URL + link["href"] if link["href"].startswith("/") else link["href"]
            else:
                return None
            
            # Find company
            company_elem = card.find("span", {"data-testid": "company-name"}) or \
                          card.find("span", class_=re.compile(r"companyName"))
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Find location
            location_elem = card.find("div", {"data-testid": "text-location"}) or \
                           card.find("div", class_=re.compile(r"companyLocation"))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Check for remote
            work_mode = "remote" if "remote" in location.lower() else ""
            
            # Find salary if available
            salary_elem = card.find("div", class_=re.compile(r"salary-snippet")) or \
                         card.find("span", class_=re.compile(r"salary"))
            salary = salary_elem.get_text(strip=True) if salary_elem else None
            
            # Find job snippet/description
            snippet_elem = card.find("div", class_=re.compile(r"job-snippet"))
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Check for easy apply
            easy_apply = bool(card.find("span", class_=re.compile(r"iaLabel")))
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "description": snippet,
                "work_mode": work_mode,
                "is_easy_apply": easy_apply,
                "salary_text": salary,
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing job card: {e}")
            return None
    
    def parse_job_page(self, url: str) -> Dict[str, Any]:
        """Parse a full job listing page.
        
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
        description_elem = soup.find("div", {"id": "jobDescriptionText"}) or \
                          soup.find("div", class_=re.compile(r"jobsearch-jobDescriptionText"))
        if description_elem:
            job_data["description"] = description_elem.get_text(separator="\n", strip=True)
        
        # Find job details
        details_elem = soup.find("div", class_=re.compile(r"jobsearch-JobInfoHeader"))
        if details_elem:
            # Extract job type
            job_type_elem = details_elem.find(string=re.compile(r"Full-time|Part-time|Contract|Internship", re.I))
            if job_type_elem:
                job_data["job_type"] = job_type_elem.strip()
        
        return job_data
