"""
Glassdoor Job Scraper

Scrapes job listings from Glassdoor.com
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode, quote

from .base_scraper import BaseScraper


class GlassdoorScraper(BaseScraper):
    """Scraper for Glassdoor job listings."""
    
    BASE_URL = "https://www.glassdoor.com"
    SEARCH_URL = "https://www.glassdoor.com/Job/jobs.htm"
    
    @property
    def platform_name(self) -> str:
        return "glassdoor"
    
    def search_jobs(self, keywords: List[str], location: str = "",
                    job_type: str = "", work_mode: str = "") -> List[Dict[str, Any]]:
        """Search for jobs on Glassdoor.
        
        Args:
            keywords: Search keywords
            location: Location filter
            job_type: Job type filter
            work_mode: Work mode filter
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        query = " ".join(keywords)
        
        # Build search parameters
        params = {
            "sc.keyword": query,
            "suggestCount": 0,
            "suggestChosen": "false",
            "clickSource": "searchBtn",
            "typedKeyword": query,
            "fromAge": 7,  # Last 7 days
        }
        
        if location:
            params["locT"] = "C"  # City
            params["locKeyword"] = location
        
        # Add remote filter
        if work_mode.lower() in ["remote", "work from home", "wfh"]:
            params["remoteWorkType"] = 1
        
        search_url = f"{self.SEARCH_URL}?{urlencode(params)}"
        self.logger.info(f"Searching Glassdoor: {search_url}")
        
        response = self.make_request(search_url)
        if not response:
            return jobs
        
        soup = self.parse_html(response.text)
        
        # Find job cards
        job_cards = soup.find_all("li", class_=re.compile(r"react-job-listing"))
        
        if not job_cards:
            job_cards = soup.find_all("div", {"data-test": "jobListing"})
        
        for card in job_cards[:self.max_jobs]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Failed to parse Glassdoor job card: {e}")
                continue
        
        self.logger.info(f"Found {len(jobs)} jobs on Glassdoor")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a Glassdoor job card.
        
        Args:
            card: BeautifulSoup element for job card
            
        Returns:
            Job dictionary or None
        """
        try:
            # Find title and link
            title_elem = card.find("a", {"data-test": "job-link"}) or \
                        card.find("a", class_=re.compile(r"job-title"))
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            job_url = title_elem.get("href", "")
            
            if job_url and not job_url.startswith("http"):
                job_url = self.BASE_URL + job_url
            
            if not job_url:
                return None
            
            # Find company
            company_elem = card.find("span", class_=re.compile(r"employer-name")) or \
                          card.find("div", {"data-test": "employer-name"})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Find location
            location_elem = card.find("span", class_=re.compile(r"location")) or \
                           card.find("span", {"data-test": "emp-location"})
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Check for remote
            work_mode = ""
            if "remote" in location.lower():
                work_mode = "remote"
            
            # Find salary
            salary_elem = card.find("span", {"data-test": "detailedSalary"}) or \
                         card.find("span", class_=re.compile(r"salary"))
            salary = salary_elem.get_text(strip=True) if salary_elem else ""
            
            # Find rating
            rating_elem = card.find("span", class_=re.compile(r"ratingNum"))
            rating = rating_elem.get_text(strip=True) if rating_elem else ""
            
            # Check for easy apply
            easy_apply = bool(card.find("span", string=re.compile(r"Easy Apply", re.I)))
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "work_mode": work_mode,
                "salary_text": salary,
                "company_rating": rating,
                "is_easy_apply": easy_apply,
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing Glassdoor job card: {e}")
            return None
    
    def parse_job_page(self, url: str) -> Dict[str, Any]:
        """Parse a full Glassdoor job listing page.
        
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
        description_elem = soup.find("div", class_=re.compile(r"jobDescriptionContent")) or \
                          soup.find("div", {"data-test": "description"})
        if description_elem:
            job_data["description"] = description_elem.get_text(separator="\n", strip=True)
        
        return job_data
