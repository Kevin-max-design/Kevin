"""
Form Filler

Automates filling job application forms using Selenium/Playwright.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..database import Job, Application, get_database
from ..llm import CoverLetterGenerator, QuestionAnswerer


class FormFiller:
    """Automates job application form filling."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize form filler.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.db = get_database(config.get("database", {}).get("path", "data/jobs.db"))
        self.cover_letter_gen = CoverLetterGenerator(config)
        self.question_answerer = QuestionAnswerer(config)
        self.logger = logging.getLogger(__name__)
        
        self.dry_run = config.get("application", {}).get("dry_run", True)
        self.driver = None
    
    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        if self.driver:
            return
        
        options = Options()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Add user agent
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
    
    def _close_driver(self):
        """Close WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def apply_to_job(self, job: Job, profile: Dict[str, Any]) -> bool:
        """Apply to a job.
        
        Args:
            job: Job object
            profile: User profile
            
        Returns:
            True if application submitted successfully
        """
        self.logger.info(f"Applying to: {job.title} at {job.company}")
        
        try:
            # Generate cover letter
            job_dict = job.to_dict()
            job_dict["description"] = job.description  # Add full description
            cover_letter = self.cover_letter_gen.generate(job_dict, profile)
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would apply to {job.title}")
                self._save_application(job, cover_letter, "dry_run")
                return True
            
            # Determine application method
            if job.is_easy_apply:
                success = self._easy_apply(job, profile, cover_letter)
            else:
                success = self._external_apply(job, profile, cover_letter)
            
            if success:
                self._save_application(job, cover_letter, "submitted")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Application failed: {e}")
            return False
    
    def _easy_apply(self, job: Job, profile: Dict[str, Any], 
                    cover_letter: str) -> bool:
        """Handle easy apply applications (LinkedIn, Indeed).
        
        Args:
            job: Job object
            profile: User profile
            cover_letter: Generated cover letter
            
        Returns:
            True if successful
        """
        self._init_driver()
        
        try:
            # Navigate to job page
            self.driver.get(job.url)
            time.sleep(2)
            
            # Platform-specific handling
            if "linkedin" in job.platform.lower():
                return self._linkedin_easy_apply(profile, cover_letter)
            elif "indeed" in job.platform.lower():
                return self._indeed_easy_apply(profile, cover_letter)
            else:
                self.logger.warning(f"Easy apply not implemented for {job.platform}")
                return False
                
        except Exception as e:
            self.logger.error(f"Easy apply failed: {e}")
            return False
        finally:
            self._close_driver()
    
    def _linkedin_easy_apply(self, profile: Dict[str, Any], 
                              cover_letter: str) -> bool:
        """Handle LinkedIn Easy Apply.
        
        Note: Requires LinkedIn login session.
        """
        try:
            # Click Easy Apply button
            apply_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-control-name='jobdetails_topcard_inapply']"))
            )
            apply_btn.click()
            time.sleep(1)
            
            # Handle multi-step form
            while True:
                # Check for submit button
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Submit application']")
                    submit_btn.click()
                    self.logger.info("Application submitted!")
                    return True
                except NoSuchElementException:
                    pass
                
                # Fill any text fields
                self._fill_form_fields(profile)
                
                # Look for next button
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "[aria-label='Continue to next step']")
                    next_btn.click()
                    time.sleep(1)
                except NoSuchElementException:
                    break
            
            return False
            
        except TimeoutException:
            self.logger.error("Easy Apply button not found")
            return False
    
    def _indeed_easy_apply(self, profile: Dict[str, Any], 
                           cover_letter: str) -> bool:
        """Handle Indeed Easy Apply."""
        try:
            # Click apply button
            apply_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#applyButtonLinkContainer button"))
            )
            apply_btn.click()
            time.sleep(2)
            
            # Fill form fields
            self._fill_form_fields(profile)
            
            # Handle resume upload if needed
            self._upload_resume(profile)
            
            # Submit
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "[type='submit']")
                submit_btn.click()
                return True
            except NoSuchElementException:
                return False
                
        except TimeoutException:
            self.logger.error("Apply button not found")
            return False
    
    def _external_apply(self, job: Job, profile: Dict[str, Any],
                        cover_letter: str) -> bool:
        """Handle external application (redirect to company site).
        
        For external applications, we prepare the materials but let the user
        complete the application manually.
        """
        self.logger.info(f"External application - materials prepared for: {job.url}")
        
        # Save the prepared materials
        self._save_application(job, cover_letter, "pending_external")
        
        return True
    
    def _fill_form_fields(self, profile: Dict[str, Any]):
        """Fill common form fields.
        
        Args:
            profile: User profile
        """
        personal = profile.get("personal", {})
        
        field_mappings = {
            "name": personal.get("name", ""),
            "email": personal.get("email", ""),
            "phone": personal.get("phone", ""),
            "linkedin": personal.get("linkedin_url", ""),
            "github": personal.get("github_url", ""),
        }
        
        for field_name, value in field_mappings.items():
            if not value:
                continue
            
            # Try various selectors
            selectors = [
                f"input[name*='{field_name}']",
                f"input[id*='{field_name}']",
                f"input[placeholder*='{field_name}']",
            ]
            
            for selector in selectors:
                try:
                    field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if field.is_displayed() and not field.get_attribute("value"):
                        field.clear()
                        field.send_keys(value)
                        break
                except NoSuchElementException:
                    continue
    
    def _upload_resume(self, profile: Dict[str, Any]):
        """Upload resume file if field exists."""
        resume_path = profile.get("resume_path", "data/resume.pdf")
        
        try:
            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(resume_path)
            time.sleep(1)
        except NoSuchElementException:
            pass
    
    def _save_application(self, job: Job, cover_letter: str, status: str):
        """Save application to database.
        
        Args:
            job: Job object
            cover_letter: Generated cover letter
            status: Application status
        """
        with self.db.get_session() as session:
            # Update job status
            db_job = session.query(Job).get(job.id)
            if db_job:
                db_job.status = "applied"
            
            # Create application record
            application = Application(
                job_id=job.id,
                cover_letter=cover_letter,
                status=status,
                applied_at=datetime.utcnow(),
            )
            session.add(application)
        
        self.logger.info(f"Application saved: {job.title} - {status}")
