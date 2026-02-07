"""
Resume Tailor

Customizes resume content for specific job applications.
"""

from typing import Dict, Any, List
import logging

from .ollama_client import OllamaClient


class ResumeTailor:
    """Tailors resume content for specific job applications."""
    
    SYSTEM_PROMPT = """You are an expert resume writer specializing in tech and data science roles.
Your task is to help tailor resume content to specific job requirements while maintaining honesty.
Focus on:
- Highlighting relevant skills and experiences
- Using keywords from the job description
- Quantifying achievements where possible
- Keeping content concise and impactful"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize resume tailor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
    
    def tailor_summary(self, profile: Dict[str, Any], job: Dict[str, Any]) -> str:
        """Generate a tailored professional summary.
        
        Args:
            profile: User profile
            job: Target job details
            
        Returns:
            Tailored summary paragraph
        """
        prompt = f"""Create a compelling professional summary (2-3 sentences) for this candidate applying to this job:

**Candidate:**
- Education: {profile.get('education', {}).get('degree', 'Computer Science degree')} in {profile.get('education', {}).get('specialization', 'Data Science')}
- Key Skills: {', '.join(profile.get('skills', {}).get('domains', [])[:5])}
- Tools: {', '.join(profile.get('skills', {}).get('tools', [])[:5])}

**Target Job:**
- Title: {job.get('title', 'Data Scientist')}
- Company: {job.get('company', '')}
- Key Requirements: {job.get('description', '')[:500]}

Write a professional summary that positions the candidate as ideal for this role."""

        return self.llm.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.6,
        ).strip()
    
    def extract_relevant_skills(self, profile: Dict[str, Any], 
                                 job: Dict[str, Any]) -> List[str]:
        """Extract the most relevant skills for a job.
        
        Args:
            profile: User profile
            job: Target job
            
        Returns:
            List of relevant skills ordered by relevance
        """
        # Get all user skills
        all_skills = []
        for category in ["programming", "domains", "tools", "cloud"]:
            all_skills.extend(profile.get("skills", {}).get(category, []))
        
        job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}".lower()
        
        # Score skills by presence in job description
        skill_scores = []
        for skill in all_skills:
            score = 0
            skill_lower = skill.lower()
            
            # Direct mention
            if skill_lower in job_text:
                score += 10
            
            # Partial match
            for word in skill_lower.split():
                if word in job_text:
                    score += 3
            
            skill_scores.append((skill, score))
        
        # Sort by score and return
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in skill_scores]
    
    def suggest_improvements(self, profile: Dict[str, Any], 
                            job: Dict[str, Any]) -> List[str]:
        """Suggest improvements for the application.
        
        Args:
            profile: User profile
            job: Target job
            
        Returns:
            List of suggestions
        """
        prompt = f"""Analyze this candidate's profile against the job requirements and provide 3-5 specific suggestions for improving their application:

**Candidate Skills:**
{', '.join(profile.get('skills', {}).get('domains', []))}
{', '.join(profile.get('skills', {}).get('tools', []))}

**Job Requirements:**
{job.get('description', '')[:800]}

Provide actionable suggestions (one per line, no numbering):"""

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.6,
        )
        
        # Parse suggestions
        suggestions = [s.strip() for s in response.strip().split('\n') if s.strip()]
        return suggestions[:5]
    
    def generate_bullet_points(self, experience: str, job: Dict[str, Any], 
                               count: int = 3) -> List[str]:
        """Generate resume bullet points for an experience.
        
        Args:
            experience: Description of the experience/project
            job: Target job
            count: Number of bullet points to generate
            
        Returns:
            List of bullet point strings
        """
        prompt = f"""Based on this experience and the target job, write {count} impactful resume bullet points:

**Experience/Project:**
{experience}

**Target Job Keywords:**
{job.get('title', '')} - {job.get('description', '')[:300]}

Write {count} bullet points that:
- Start with action verbs
- Include metrics where possible
- Align with the job requirements
- Are concise (one line each)

Format: One bullet point per line, starting with "• " """

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.6,
        )
        
        # Parse bullet points
        bullets = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line.startswith('•'):
                line = line[1:].strip()
            if line.startswith('-'):
                line = line[1:].strip()
            if line:
                bullets.append(line)
        
        return bullets[:count]
