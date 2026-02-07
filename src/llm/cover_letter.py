"""
Cover Letter Generator

Generates personalized cover letters using LLM.
"""

from typing import Dict, Any
import logging

from .ollama_client import OllamaClient


class CoverLetterGenerator:
    """Generates tailored cover letters for job applications."""
    
    SYSTEM_PROMPT = """You are an expert career coach and professional writer specializing in cover letters for tech roles. 
Your task is to write compelling, personalized cover letters that:
- Highlight relevant skills and experience
- Show genuine interest in the company and role
- Are concise and professional (250-350 words)
- Avoid generic phrases and clichés
- Include specific examples when possible
- End with a clear call to action"""

    COVER_LETTER_TEMPLATE = """Write a professional cover letter for the following job application.

**Candidate Profile:**
- Name: {name}
- Education: {education}
- Skills: {skills}
- Experience: {experience}

**Job Details:**
- Position: {job_title}
- Company: {company}
- Location: {location}
- Job Description: {job_description}

Write a compelling cover letter that connects the candidate's background to this specific role. 
Make it personal, specific, and avoid generic phrases.
Do not include the header (address, date, etc.) - start directly with the greeting.
"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize cover letter generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
    
    def generate(self, job: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """Generate a cover letter for a job application.
        
        Args:
            job: Job details dictionary
            profile: User profile dictionary
            
        Returns:
            Generated cover letter text
        """
        # Extract profile info
        personal = profile.get("personal", {})
        skills_config = profile.get("skills", {})
        education = profile.get("education", {})
        experience = profile.get("experience", {})
        
        # Format skills
        all_skills = []
        for category in ["programming", "domains", "tools"]:
            all_skills.extend(skills_config.get(category, []))
        skills_str = ", ".join(all_skills[:10])  # Limit to top 10
        
        # Format education
        education_str = f"{education.get('degree', 'Degree')} with specialization in {education.get('specialization', 'Computer Science')}"
        
        # Format experience
        experience_str = experience.get("summary", "Fresh graduate with strong technical skills")
        if experience.get("years", 0) > 0:
            experience_str = f"{experience['years']} years of experience. {experience_str}"
        
        # Build prompt
        prompt = self.COVER_LETTER_TEMPLATE.format(
            name=personal.get("name", "Candidate"),
            education=education_str,
            skills=skills_str,
            experience=experience_str,
            job_title=job.get("title", "Position"),
            company=job.get("company", "Company"),
            location=job.get("location", ""),
            job_description=job.get("description", "")[:1500],  # Limit description length
        )
        
        self.logger.info(f"Generating cover letter for {job.get('title')} at {job.get('company')}")
        
        # Generate with LLM
        cover_letter = self.llm.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.7,
        )
        
        if not cover_letter:
            self.logger.warning("LLM generation failed, using fallback template")
            cover_letter = self._generate_fallback(job, profile)
        
        return cover_letter.strip()
    
    def _generate_fallback(self, job: Dict[str, Any], profile: Dict[str, Any]) -> str:
        """Generate a simple fallback cover letter if LLM fails.
        
        Args:
            job: Job details
            profile: User profile
            
        Returns:
            Basic cover letter
        """
        personal = profile.get("personal", {})
        name = personal.get("name", "")
        education = profile.get("education", {})
        
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.get('title', 'position')} role at {job.get('company', 'your company')}. With my background in {education.get('specialization', 'Computer Science')} and passion for {profile.get('skills', {}).get('domains', ['technology'])[0] if profile.get('skills', {}).get('domains') else 'technology'}, I am confident I would be a valuable addition to your team.

My technical skills include proficiency in {', '.join(profile.get('skills', {}).get('programming', ['Python']))} and experience with {', '.join(profile.get('skills', {}).get('tools', ['various tools'])[:3])}. I am particularly drawn to this opportunity because it aligns perfectly with my career goals and interests.

I am eager to bring my skills and enthusiasm to {job.get('company', 'your team')} and contribute to your ongoing success. I would welcome the opportunity to discuss how my background and skills would benefit your organization.

Thank you for considering my application.

Best regards,
{name if name else 'Candidate'}"""
    
    def refine_cover_letter(self, cover_letter: str, feedback: str) -> str:
        """Refine an existing cover letter based on feedback.
        
        Args:
            cover_letter: Original cover letter
            feedback: User feedback or requirements
            
        Returns:
            Refined cover letter
        """
        prompt = f"""Please refine this cover letter based on the following feedback:

**Original Cover Letter:**
{cover_letter}

**Feedback:**
{feedback}

Rewrite the cover letter incorporating this feedback while maintaining a professional tone."""

        return self.llm.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.6,
        ).strip()
