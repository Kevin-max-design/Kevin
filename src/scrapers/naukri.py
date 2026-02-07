"""
Naukri Job Scraper

Scrapes job listings from Naukri.com (Indian job portal)
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode, quote

from .base_scraper import BaseScraper


class NaukriScraper(BaseScraper):
    """Scraper for Naukri.com job listings."""
    
    BASE_URL = "https://www.naukri.com"
    
    @property
    def platform_name(self) -> str:
        return "naukri"
    
    def search_jobs(self, keywords: List[str], location: str = "",
                    job_type: str = "", work_mode: str = "") -> List[Dict[str, Any]]:
        """Search for jobs on Naukri.
        
        Args:
            keywords: Search keywords
            location: Location filter
            job_type: Job type filter
            work_mode: Work mode filter
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        query = "-".join(keywords).lower().replace(" ", "-")
        
        # Build search URL - Naukri uses path-based search
        search_path = f"{query}-jobs"
        
        if work_mode.lower() in ["remote", "work from home", "wfh"]:
            search_path += "-work-from-home"
        
        if location:
            search_path += f"-in-{location.lower().replace(' ', '-')}"
        
        search_url = f"{self.BASE_URL}/{search_path}?sort=date"
        
        # Add job type filter
        if job_type.lower() == "internship":
            search_url += "&jobType=internship"
        elif job_type.lower() == "full-time":
            search_url += "&jobType=fulltime"
        
        self.logger.info(f"Searching Naukri: {search_url}")
        
        response = self.make_request(search_url)
        if not response:
            return jobs
        
        soup = self.parse_html(response.text)
        
        # Find job cards
        job_cards = soup.find_all("article", class_=re.compile(r"jobTuple"))
        
        if not job_cards:
            job_cards = soup.find_all("div", class_=re.compile(r"srp-jobtuple"))
        
        if not job_cards:
            job_cards = soup.find_all("div", {"data-job-id": True})
        
        for card in job_cards[:self.max_jobs]:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Failed to parse Naukri job card: {e}")
                continue
        
        self.logger.info(f"Found {len(jobs)} jobs on Naukri")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse a Naukri job card.
        
        Args:
            card: BeautifulSoup element for job card
            
        Returns:
            Job dictionary or None
        """
        try:
            # Find title
            title_elem = card.find("a", class_=re.compile(r"title")) or \
                        card.find("a", class_=re.compile(r"desig"))
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            job_url = title_elem.get("href", "")
            
            if not job_url or not job_url.startswith("http"):
                return None
            
            # Find company
            company_elem = card.find("a", class_=re.compile(r"comp-name")) or \
                          card.find("span", class_=re.compile(r"companyName"))
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Find location
            location_elem = card.find("span", class_=re.compile(r"loc")) or \
                           card.find("span", class_=re.compile(r"locWdth"))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Check for remote
            work_mode = ""
            if "remote" in location.lower() or "work from home" in location.lower():
                work_mode = "remote"
            
            # Find experience
            exp_elem = card.find("span", class_=re.compile(r"exp"))
            experience = exp_elem.get_text(strip=True) if exp_elem else ""
            
            # Find salary
            salary_elem = card.find("span", class_=re.compile(r"sal"))
            salary = salary_elem.get_text(strip=True) if salary_elem else ""
            
            # Find job description snippet
            desc_elem = card.find("span", class_=re.compile(r"job-desc")) or \
                       card.find("div", class_=re.compile(r"job-description"))
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Check for easy apply
            easy_apply = bool(card.find("span", string=re.compile(r"Apply|Easy", re.I)))
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "description": description,
                "work_mode": work_mode,
                "experience_required": experience,
                "salary_text": salary,
                "is_easy_apply": easy_apply,
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing Naukri job card: {e}")
            return None
    
    def parse_job_page(self, url: str) -> Dict[str, Any]:
        """Parse a full Naukri job listing page.
        
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
        description_elem = soup.find("div", class_=re.compile(r"job-desc")) or \
                          soup.find("section", class_=re.compile(r"job-description"))
        if description_elem:
            job_data["description"] = description_elem.get_text(separator="\n", strip=True)
        
        # Find skills
        skills_section = soup.find("div", class_=re.compile(r"key-skill"))
        if skills_section:
            skills = [s.get_text(strip=True) for s in skills_section.find_all("a")]
            job_data["required_skills"] = skills
        
        return job_data
