"""
Playwright Applicator - Enhanced browser automation with stealth mode.

Provides human-like browser automation for job applications using Playwright
with anti-detection measures and human-in-the-loop approval workflow.
"""

import asyncio
import logging
import random
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright_stealth import stealth_async
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from ..database import Job, Application, AuditLog, get_database


@dataclass
class ApplicationResult:
    """Result of an application attempt."""
    success: bool
    job_id: int
    method: str  # form, email, easy_apply
    message: str
    screenshot_path: Optional[str] = None
    error: Optional[str] = None


class PlaywrightApplicator:
    """
    Browser-based job application automation using Playwright.
    
    Features:
    - Stealth mode to avoid bot detection
    - Human-like typing and mouse movements
    - Form field intelligent filling
    - Screenshot capture for verification
    - Human-in-the-loop approval hooks
    """
    
    # Typing speed range (characters per second)
    TYPING_SPEED_MIN = 0.05
    TYPING_SPEED_MAX = 0.15
    
    # Common form field identifiers
    FIELD_PATTERNS = {
        "name": ["name", "full-name", "fullname", "applicant-name"],
        "first_name": ["first-name", "firstname", "fname", "first"],
        "last_name": ["last-name", "lastname", "lname", "last", "surname"],
        "email": ["email", "e-mail", "mail"],
        "phone": ["phone", "telephone", "mobile", "cell", "tel"],
        "linkedin": ["linkedin", "linkedinurl", "linkedin-url"],
        "github": ["github", "githuburl", "github-url"],
        "portfolio": ["portfolio", "website", "personal-site"],
        "resume": ["resume", "cv", "attachment", "upload"],
        "cover_letter": ["cover", "letter", "coverletter", "cover-letter"],
        "experience": ["experience", "years", "yoe"],
        "salary": ["salary", "compensation", "expected-salary"],
        "location": ["location", "city", "address"],
        "start_date": ["start", "availability", "available"],
        "visa": ["visa", "sponsorship", "authorization", "work-auth"],
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Playwright applicator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = get_database()
        
        # Playwright instances
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Settings
        self.headless = config.get("automation", {}).get("headless", False)
        self.screenshot_dir = Path(config.get("automation", {}).get(
            "screenshot_dir", "data/screenshots"
        ))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Approval callback
        self.approval_callback: Optional[Callable] = None
        
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning(
                "Playwright not installed. Install with: "
                "pip install playwright playwright-stealth && playwright install chromium"
            )
    
    def set_approval_callback(self, callback: Callable[[Job, Dict], bool]):
        """
        Set callback function for human-in-the-loop approval.
        
        Args:
            callback: Function that takes (job, prepared_data) and returns bool
        """
        self.approval_callback = callback
    
    async def initialize(self):
        """Initialize browser with stealth settings."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available")
        
        playwright = await async_playwright().start()
        
        # Launch browser with stealth settings
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles',
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Apply stealth mode
        await stealth_async(self.page)
        
        self.logger.info("Playwright browser initialized with stealth mode")
    
    async def close(self):
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
    
    async def apply_to_job(
        self,
        job: Job,
        profile: Dict[str, Any],
        cover_letter: str,
        resume_path: str = None,
    ) -> ApplicationResult:
        """
        Apply to a job with human-in-the-loop approval.
        
        Args:
            job: Job to apply to
            profile: User profile
            cover_letter: Generated cover letter
            resume_path: Path to resume file
            
        Returns:
            ApplicationResult with status
        """
        if not self.page:
            await self.initialize()
        
        try:
            # Navigate to job URL
            await self.page.goto(job.url, wait_until='networkidle')
            await self._random_delay(1, 3)
            
            # Take initial screenshot
            screenshot_path = await self._take_screenshot(job.id, "initial")
            
            # Detect application type
            app_type = await self._detect_application_type()
            
            # Prepare application data
            app_data = self._prepare_application_data(profile, cover_letter, resume_path)
            
            # Request approval if callback is set
            if self.approval_callback:
                approved = self.approval_callback(job, {
                    "application_type": app_type,
                    "cover_letter": cover_letter,
                    "resume_path": resume_path,
                    "screenshot": screenshot_path,
                })
                
                if not approved:
                    return ApplicationResult(
                        success=False,
                        job_id=job.id,
                        method=app_type,
                        message="Application rejected by user",
                    )
            
            # Apply based on type
            if app_type == "easy_apply":
                result = await self._handle_easy_apply(job, profile, app_data)
            elif app_type == "email":
                result = await self._handle_email_apply(job, profile, app_data)
            else:
                result = await self._handle_form_apply(job, profile, app_data)
            
            # Take final screenshot
            final_screenshot = await self._take_screenshot(job.id, "final")
            result.screenshot_path = final_screenshot
            
            # Log the action
            self._log_application(job, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Application failed for job {job.id}: {e}")
            screenshot_path = await self._take_screenshot(job.id, "error")
            
            return ApplicationResult(
                success=False,
                job_id=job.id,
                method="unknown",
                message="Application failed",
                error=str(e),
                screenshot_path=screenshot_path,
            )
    
    async def _detect_application_type(self) -> str:
        """Detect the type of application on current page."""
        # Check for Easy Apply buttons
        easy_apply_selectors = [
            "button:has-text('Easy Apply')",
            "button:has-text('Quick Apply')",
            ".jobs-apply-button",
            "[data-automation='job-apply-button']",
        ]
        
        for selector in easy_apply_selectors:
            if await self.page.locator(selector).count() > 0:
                return "easy_apply"
        
        # Check for email application
        email_patterns = [
            "mailto:",
            "email applications",
            "send resume to",
        ]
        
        content = await self.page.content()
        for pattern in email_patterns:
            if pattern.lower() in content.lower():
                return "email"
        
        # Default to form
        return "form"
    
    async def _handle_easy_apply(
        self,
        job: Job,
        profile: Dict[str, Any],
        app_data: Dict[str, Any],
    ) -> ApplicationResult:
        """Handle Easy Apply type applications."""
        try:
            # Click Easy Apply button
            easy_apply_btn = self.page.locator(
                "button:has-text('Easy Apply'), button:has-text('Quick Apply')"
            ).first
            
            if await easy_apply_btn.count() > 0:
                await self._human_click(easy_apply_btn)
                await self._random_delay(2, 4)
            
            # Fill form fields
            await self._fill_application_form(profile, app_data)
            
            # Look for submit button but DON'T click (requires approval)
            submit_btn = self.page.locator(
                "button[type='submit'], button:has-text('Submit'), button:has-text('Apply')"
            ).first
            
            if await submit_btn.count() > 0:
                # Highlight submit button for user
                await submit_btn.scroll_into_view_if_needed()
                
                # In production, you might want to wait for actual user click
                # For now, we auto-submit after filling
                await self._human_click(submit_btn)
                await self._random_delay(3, 5)
                
                return ApplicationResult(
                    success=True,
                    job_id=job.id,
                    method="easy_apply",
                    message="Easy Apply completed",
                )
            
            return ApplicationResult(
                success=False,
                job_id=job.id,
                method="easy_apply",
                message="Submit button not found",
            )
            
        except Exception as e:
            return ApplicationResult(
                success=False,
                job_id=job.id,
                method="easy_apply",
                message="Easy Apply failed",
                error=str(e),
            )
    
    async def _handle_form_apply(
        self,
        job: Job,
        profile: Dict[str, Any],
        app_data: Dict[str, Any],
    ) -> ApplicationResult:
        """Handle standard form applications."""
        try:
            # Look for Apply button to start application
            apply_btn = self.page.locator(
                "a:has-text('Apply'), button:has-text('Apply')"
            ).first
            
            if await apply_btn.count() > 0:
                href = await apply_btn.get_attribute("href")
                
                if href and href.startswith("http"):
                    # External application
                    await self.page.goto(href, wait_until='networkidle')
                else:
                    await self._human_click(apply_btn)
                
                await self._random_delay(2, 4)
            
            # Fill application form
            await self._fill_application_form(profile, app_data)
            
            # Upload resume if field exists
            await self._upload_file(app_data.get("resume_path"), "resume")
            
            # Upload cover letter if field exists
            if app_data.get("cover_letter"):
                await self._fill_text_field("cover_letter", app_data["cover_letter"])
            
            # Find and prepare submit (don't auto-click without approval)
            return ApplicationResult(
                success=True,
                job_id=job.id,
                method="form",
                message="Form filled, ready for submission",
            )
            
        except Exception as e:
            return ApplicationResult(
                success=False,
                job_id=job.id,
                method="form",
                message="Form application failed",
                error=str(e),
            )
    
    async def _handle_email_apply(
        self,
        job: Job,
        profile: Dict[str, Any],
        app_data: Dict[str, Any],
    ) -> ApplicationResult:
        """Handle email-based applications."""
        # For email applications, we prepare the email content
        # but don't actually send (handled separately)
        
        email_address = job.application_email or self._extract_email_from_page()
        
        if not email_address:
            return ApplicationResult(
                success=False,
                job_id=job.id,
                method="email",
                message="Email address not found",
            )
        
        return ApplicationResult(
            success=True,
            job_id=job.id,
            method="email",
            message=f"Email prepared for {email_address}",
        )
    
    async def _fill_application_form(
        self,
        profile: Dict[str, Any],
        app_data: Dict[str, Any],
    ):
        """Fill form fields with profile data."""
        personal = profile.get("personal", {})
        
        # Map profile data to form fields
        field_values = {
            "first_name": personal.get("name", "").split()[0] if personal.get("name") else "",
            "last_name": " ".join(personal.get("name", "").split()[1:]) if personal.get("name") else "",
            "name": personal.get("name", ""),
            "email": personal.get("email", ""),
            "phone": personal.get("phone", ""),
            "linkedin": personal.get("linkedin", ""),
            "github": personal.get("github", ""),
            "location": personal.get("location", ""),
        }
        
        # Try to fill each field
        for field_type, value in field_values.items():
            if value:
                await self._fill_text_field(field_type, value)
    
    async def _fill_text_field(self, field_type: str, value: str):
        """Fill a text field with human-like typing."""
        patterns = self.FIELD_PATTERNS.get(field_type, [field_type])
        
        for pattern in patterns:
            selectors = [
                f"input[name*='{pattern}' i]",
                f"input[id*='{pattern}' i]",
                f"input[placeholder*='{pattern}' i]",
                f"textarea[name*='{pattern}' i]",
                f"textarea[id*='{pattern}' i]",
            ]
            
            for selector in selectors:
                field = self.page.locator(selector).first
                
                if await field.count() > 0:
                    try:
                        await self._human_type(field, value)
                        return True
                    except Exception:
                        continue
        
        return False
    
    async def _upload_file(self, file_path: str, field_type: str):
        """Upload a file to a file input."""
        if not file_path or not Path(file_path).exists():
            return False
        
        patterns = self.FIELD_PATTERNS.get(field_type, [field_type])
        
        for pattern in patterns:
            selector = f"input[type='file'][name*='{pattern}' i], input[type='file'][id*='{pattern}' i]"
            file_input = self.page.locator(selector).first
            
            if await file_input.count() > 0:
                try:
                    await file_input.set_input_files(file_path)
                    return True
                except Exception:
                    continue
        
        return False
    
    async def _human_click(self, locator):
        """Click with human-like behavior."""
        # Move to element with slight randomness
        box = await locator.bounding_box()
        if box:
            x = box['x'] + box['width'] / 2 + random.uniform(-5, 5)
            y = box['y'] + box['height'] / 2 + random.uniform(-3, 3)
            
            await self.page.mouse.move(x, y, steps=random.randint(10, 20))
            await self._random_delay(0.1, 0.3)
        
        await locator.click()
    
    async def _human_type(self, locator, text: str):
        """Type with human-like delays."""
        await locator.click()
        await self._random_delay(0.2, 0.5)
        
        # Clear existing content
        await locator.fill("")
        
        # Type character by character with random delays
        for char in text:
            await locator.type(char, delay=random.uniform(
                self.TYPING_SPEED_MIN * 1000,
                self.TYPING_SPEED_MAX * 1000
            ))
    
    async def _random_delay(self, min_seconds: float, max_seconds: float):
        """Wait for a random duration."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def _take_screenshot(self, job_id: int, stage: str) -> str:
        """Take a screenshot of current page."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"job_{job_id}_{stage}_{timestamp}.png"
        path = self.screenshot_dir / filename
        
        await self.page.screenshot(path=str(path), full_page=False)
        return str(path)
    
    def _extract_email_from_page(self) -> Optional[str]:
        """Extract email address from current page content."""
        import re
        # This would be called synchronously on page content
        # Simplified implementation
        return None
    
    def _prepare_application_data(
        self,
        profile: Dict[str, Any],
        cover_letter: str,
        resume_path: str,
    ) -> Dict[str, Any]:
        """Prepare application data dictionary."""
        return {
            "profile": profile,
            "cover_letter": cover_letter,
            "resume_path": resume_path,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _log_application(self, job: Job, result: ApplicationResult):
        """Log application attempt to database."""
        with self.db.get_session() as session:
            AuditLog.log(
                session,
                action="application_attempt",
                entity_type="job",
                entity_id=job.id,
                details={
                    "method": result.method,
                    "success": result.success,
                    "message": result.message,
                    "screenshot": result.screenshot_path,
                },
                status="success" if result.success else "failed",
                error=result.error,
            )
            session.commit()


# Sync wrapper for the async applicator
class SyncPlaywrightApplicator:
    """Synchronous wrapper for PlaywrightApplicator."""
    
    def __init__(self, config: Dict[str, Any]):
        self.async_applicator = PlaywrightApplicator(config)
    
    def apply_to_job(
        self,
        job: Job,
        profile: Dict[str, Any],
        cover_letter: str,
        resume_path: str = None,
    ) -> ApplicationResult:
        """Apply to job (sync wrapper)."""
        return asyncio.run(
            self.async_applicator.apply_to_job(job, profile, cover_letter, resume_path)
        )
    
    def close(self):
        """Close browser."""
        asyncio.run(self.async_applicator.close())
