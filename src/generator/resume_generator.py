"""
Resume Generator - Create tailored, ATS-optimized resumes.

Generates role-specific resume versions optimized for ATS systems
and tailored to specific job descriptions.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..llm import OllamaClient


class ResumeTailor:
    """
    Tailor resumes for specific job applications.
    
    Uses LLM to rewrite resume content to better match job requirements
    while maintaining accuracy and professionalism.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize resume tailor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
        
        # Output directory for tailored resumes
        self.output_dir = Path(config.get("generator", {}).get(
            "output_dir", "data/tailored_resumes"
        ))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def tailor_resume(
        self, 
        base_resume: Dict[str, Any],
        job: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Tailor resume for a specific job.
        
        Args:
            base_resume: Base resume data (from ResumeParser)
            job: Job data including description
            profile: User profile
            
        Returns:
            Tailored resume content and metadata
        """
        job_title = job.get("title", "Position")
        company = job.get("company", "Company")
        jd = job.get("description", "")
        
        # Get key skills from job
        job_skills = job.get("matched_skills", [])
        missing_skills = job.get("missing_skills", [])
        
        # Generate tailored content
        tailored_content = self._generate_tailored_content(
            base_resume.get("raw_text", ""),
            job_title,
            company,
            jd,
            job_skills,
            profile
        )
        
        # Generate optimized bullet points
        experience_bullets = self._generate_experience_bullets(
            base_resume,
            job_skills,
            jd
        )
        
        # Generate skills section
        skills_section = self._generate_skills_section(
            base_resume.get("skills", []),
            job_skills
        )
        
        return {
            "tailored_content": tailored_content,
            "experience_bullets": experience_bullets,
            "skills_section": skills_section,
            "job_id": job.get("id"),
            "job_title": job_title,
            "company": company,
            "tailored_at": datetime.utcnow().isoformat(),
        }
    
    def _generate_tailored_content(
        self,
        resume_text: str,
        job_title: str,
        company: str,
        jd: str,
        target_skills: List[str],
        profile: Dict[str, Any],
    ) -> str:
        """Generate ATS-optimized tailored resume content."""
        
        prompt = f"""Rewrite this resume to be optimized for the following job position.

TARGET POSITION: {job_title} at {company}

KEY REQUIREMENTS FROM JOB:
{jd[:1500]}

SKILLS TO EMPHASIZE: {', '.join(target_skills[:10]) if target_skills else 'Based on job description'}

ORIGINAL RESUME:
{resume_text[:2000]}

INSTRUCTIONS:
1. Keep all factual information accurate
2. Reorder and emphasize relevant experience
3. Use keywords from the job description naturally
4. Quantify achievements where possible
5. Make it ATS-friendly with clear section headers
6. Keep professional summary concise and targeted

Return the complete tailored resume text."""

        try:
            if self.llm.is_available():
                response = self.llm.generate(prompt, temperature=0.3)
                return response
            else:
                return self._fallback_tailor(resume_text, target_skills)
        except Exception as e:
            self.logger.error(f"Resume tailoring failed: {e}")
            return resume_text
    
    def _generate_experience_bullets(
        self,
        base_resume: Dict[str, Any],
        target_skills: List[str],
        jd: str,
    ) -> List[str]:
        """Generate tailored experience bullet points."""
        
        prompt = f"""Generate 5 impactful experience bullet points that would be relevant for a job requiring:
{', '.join(target_skills[:8]) if target_skills else 'general software development'}

Based on the job description:
{jd[:800]}

Each bullet point should:
- Start with a strong action verb
- Include quantifiable results where possible
- Be concise (1-2 lines)
- Be relevant to the target role

Return as a numbered list."""

        try:
            if self.llm.is_available():
                response = self.llm.generate(prompt, temperature=0.5)
                # Parse bullet points from response
                bullets = []
                for line in response.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        # Remove numbering/bullets
                        bullet = line.lstrip('0123456789.-•) ').strip()
                        if bullet:
                            bullets.append(bullet)
                return bullets[:5]
            return []
        except Exception as e:
            self.logger.error(f"Bullet generation failed: {e}")
            return []
    
    def _generate_skills_section(
        self,
        resume_skills: List[str],
        target_skills: List[str],
    ) -> Dict[str, List[str]]:
        """Generate optimized skills section."""
        
        # Prioritize matching skills
        matching = [s for s in resume_skills if s.lower() in [t.lower() for t in target_skills]]
        other = [s for s in resume_skills if s not in matching]
        
        # Organize by category
        categories = {
            "highlighted": matching[:10],  # Most relevant skills first
            "programming": [],
            "frameworks": [],
            "tools": [],
            "soft_skills": [],
        }
        
        programming_keywords = ["python", "java", "javascript", "c++", "sql", "r"]
        framework_keywords = ["tensorflow", "pytorch", "react", "django", "flask"]
        tool_keywords = ["git", "docker", "aws", "azure", "kubernetes"]
        
        for skill in other:
            skill_lower = skill.lower()
            if any(kw in skill_lower for kw in programming_keywords):
                categories["programming"].append(skill)
            elif any(kw in skill_lower for kw in framework_keywords):
                categories["frameworks"].append(skill)
            elif any(kw in skill_lower for kw in tool_keywords):
                categories["tools"].append(skill)
            else:
                categories["soft_skills"].append(skill)
        
        return {k: v for k, v in categories.items() if v}
    
    def _fallback_tailor(self, resume_text: str, target_skills: List[str]) -> str:
        """Fallback when LLM is not available."""
        # Simple keyword highlighting approach
        tailored = resume_text
        
        # Add a header if skills are available
        if target_skills:
            skills_line = f"\n\nKEY SKILLS: {', '.join(target_skills[:8])}\n\n"
            tailored = skills_line + tailored
        
        return tailored


class ResumeGenerator:
    """
    Generate complete resume documents.
    
    Creates resume variants for different job types:
    - Data Science focus
    - Machine Learning focus
    - General Software Engineering
    - Internship optimized
    """
    
    VARIANTS = {
        "data_science": {
            "focus_skills": ["python", "sql", "pandas", "statistics", "data analysis", 
                           "machine learning", "visualization"],
            "sections_order": ["summary", "skills", "experience", "projects", "education"],
        },
        "machine_learning": {
            "focus_skills": ["python", "tensorflow", "pytorch", "deep learning", 
                           "neural networks", "nlp", "computer vision"],
            "sections_order": ["summary", "skills", "projects", "experience", "education"],
        },
        "software_engineering": {
            "focus_skills": ["python", "java", "javascript", "docker", "aws", 
                           "git", "agile", "rest api"],
            "sections_order": ["summary", "experience", "skills", "projects", "education"],
        },
        "internship": {
            "focus_skills": ["python", "problem solving", "teamwork", 
                           "communication", "learning"],
            "sections_order": ["education", "skills", "projects", "experience"],
        },
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize resume generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tailor = ResumeTailor(config)
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
    
    def generate_variant(
        self,
        base_resume: Dict[str, Any],
        variant: str,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a resume variant for a specific job type.
        
        Args:
            base_resume: Base resume data
            variant: Variant type (data_science, machine_learning, etc.)
            profile: User profile
            
        Returns:
            Generated resume content
        """
        if variant not in self.VARIANTS:
            variant = "software_engineering"
        
        variant_config = self.VARIANTS[variant]
        
        # Extract values to avoid backslash in f-string expressions
        name = profile.get('personal', {}).get('name', 'Candidate')
        skills = ', '.join(profile.get('skills', {}).get('programming', []))
        years = profile.get('experience', {}).get('years', 0)
        degree = profile.get('education', {}).get('degree', "Bachelor's")
        resume_text = base_resume.get('raw_text', '')[:1500]
        focus_skills = ', '.join(variant_config['focus_skills'])
        sections = ', '.join(variant_config['sections_order'])
        
        prompt = f"""Create a {variant.replace('_', ' ')} focused resume based on:

PROFILE:
Name: {name}
Skills: {skills}
Experience: {years} years
Education: {degree}

BASE RESUME:
{resume_text}

FOCUS AREAS:
{focus_skills}

Create a professional resume with sections in this order:
{sections}

Make it ATS-friendly, quantify achievements, and emphasize relevant skills."""


        try:
            if self.llm.is_available():
                content = self.llm.generate(prompt, temperature=0.4)
            else:
                content = base_resume.get('raw_text', '')
            
            return {
                "variant": variant,
                "content": content,
                "focus_skills": variant_config['focus_skills'],
                "generated_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Variant generation failed: {e}")
            return {
                "variant": variant,
                "content": base_resume.get('raw_text', ''),
                "error": str(e),
            }
    
    def select_best_variant(
        self,
        job: Dict[str, Any],
        available_variants: List[str] = None,
    ) -> str:
        """
        Select the best resume variant for a job.
        
        Args:
            job: Job data with description and requirements
            available_variants: List of available variant names
            
        Returns:
            Best matching variant name
        """
        if not available_variants:
            available_variants = list(self.VARIANTS.keys())
        
        title = job.get("title", "").lower()
        jd = job.get("description", "").lower()
        job_type = job.get("job_type", "").lower()
        
        # Check for internship
        if "intern" in title or "intern" in job_type:
            return "internship"
        
        # Check for ML/AI
        ml_keywords = ["machine learning", "ml engineer", "deep learning", "ai ", 
                      "neural network", "nlp", "computer vision"]
        if any(kw in title or kw in jd for kw in ml_keywords):
            return "machine_learning"
        
        # Check for Data Science
        ds_keywords = ["data scientist", "data science", "data analyst", 
                      "analytics", "business intelligence"]
        if any(kw in title or kw in jd for kw in ds_keywords):
            return "data_science"
        
        # Default to software engineering
        return "software_engineering"
    
    def get_professional_summary(
        self,
        profile: Dict[str, Any],
        job: Dict[str, Any],
    ) -> str:
        """Generate a targeted professional summary."""
        
        # Extract values to avoid backslash in f-string expressions
        name = profile.get('personal', {}).get('name', 'Candidate')
        years = profile.get('experience', {}).get('years', 0)
        key_skills = ', '.join(profile.get('skills', {}).get('programming', [])[:5])
        degree = profile.get('education', {}).get('degree', "Bachelor's degree")
        job_title = job.get('title', 'Position')
        company = job.get('company', 'Company')
        
        prompt = f"""Write a professional summary (3-4 sentences) for:

CANDIDATE:
- Name: {name}
- Experience: {years} years
- Key Skills: {key_skills}
- Education: {degree}

TARGET ROLE: {job_title} at {company}

Write a compelling, targeted professional summary that:
- Highlights relevant experience and skills
- Shows enthusiasm for the role
- Is concise and impactful
- Does not use "I" statements

Return only the summary text."""

        try:
            if self.llm.is_available():
                return self.llm.generate(prompt, temperature=0.6)
            else:
                return self._default_summary(profile)
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            return self._default_summary(profile)
    
    def _default_summary(self, profile: Dict[str, Any]) -> str:
        """Generate a default professional summary."""
        name = profile.get('personal', {}).get('name', 'Professional')
        years = profile.get('experience', {}).get('years', 0)
        skills = profile.get('skills', {}).get('programming', ['Python'])[:3]
        
        if years > 0:
            return f"Results-driven professional with {years} years of experience in {', '.join(skills)}. Passionate about building innovative solutions and driving business impact through technology."
        else:
            return f"Motivated graduate with strong foundation in {', '.join(skills)}. Eager to apply academic knowledge and personal projects to real-world challenges in a dynamic team environment."
