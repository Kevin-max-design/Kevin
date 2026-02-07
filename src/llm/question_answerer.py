"""
Question Answerer

Uses LLM to answer job application questions intelligently.
"""

from typing import Dict, Any, List, Optional
import logging

from .ollama_client import OllamaClient


class QuestionAnswerer:
    """Answers job application questions using LLM."""
    
    SYSTEM_PROMPT = """You are helping a job candidate answer application questions.
Be professional, honest, and concise. 
For yes/no questions, answer directly.
For open-ended questions, provide thoughtful but brief responses.
Never fabricate experience or skills the candidate doesn't have."""
    
    # Common application questions and answer strategies
    COMMON_QUESTIONS = {
        "salary": "Based on market research and my experience level, I'm targeting a range that's competitive for this role. I'm open to discussing compensation that reflects the value I can bring to the team.",
        "start_date": "I can start within 2-4 weeks of receiving an offer, or I'm flexible to accommodate your timeline.",
        "relocation": "I am open to relocation for the right opportunity.",
        "sponsorship": None,  # This needs profile-specific answer
        "remote": "I am comfortable working remotely and have experience with remote collaboration tools.",
        "experience_years": None,  # Calculated from profile
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize question answerer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
    
    def answer_question(self, question: str, profile: Dict[str, Any],
                        job: Dict[str, Any] = None) -> str:
        """Answer an application question.
        
        Args:
            question: The question to answer
            profile: User profile
            job: Optional job context
            
        Returns:
            Answer text
        """
        question_lower = question.lower()
        
        # Check for common question patterns
        if any(word in question_lower for word in ["salary", "compensation", "pay"]):
            return self._answer_salary(question, profile)
        
        if any(word in question_lower for word in ["start", "when can you", "available"]):
            return self.COMMON_QUESTIONS["start_date"]
        
        if any(word in question_lower for word in ["relocate", "relocation", "move"]):
            return self._answer_relocation(question, profile)
        
        if any(word in question_lower for word in ["sponsor", "visa", "authorization"]):
            return self._answer_sponsorship(question, profile)
        
        if any(word in question_lower for word in ["remote", "work from home", "hybrid"]):
            return self.COMMON_QUESTIONS["remote"]
        
        if any(word in question_lower for word in ["years", "experience"]):
            return self._answer_experience(question, profile)
        
        # Use LLM for other questions
        return self._generate_answer(question, profile, job)
    
    def _answer_salary(self, question: str, profile: Dict[str, Any]) -> str:
        """Answer salary-related questions."""
        min_salary = profile.get("preferences", {}).get("min_salary", 0)
        if min_salary > 0:
            return f"My salary expectation is around {min_salary:,} per year, though I'm open to discussing a package that reflects the role's responsibilities and growth opportunities."
        return self.COMMON_QUESTIONS["salary"]
    
    def _answer_relocation(self, question: str, profile: Dict[str, Any]) -> str:
        """Answer relocation questions."""
        work_modes = profile.get("preferences", {}).get("work_mode", [])
        if "Remote" in work_modes or "Work from Home" in work_modes:
            return "I prefer remote work, but I am open to discussing relocation for the right opportunity."
        return self.COMMON_QUESTIONS["relocation"]
    
    def _answer_sponsorship(self, question: str, profile: Dict[str, Any]) -> str:
        """Answer work authorization questions."""
        # This should be customized based on actual user situation
        return "I am authorized to work in the country and do not require visa sponsorship."
    
    def _answer_experience(self, question: str, profile: Dict[str, Any]) -> str:
        """Answer experience-related questions."""
        years = profile.get("experience", {}).get("years", 0)
        if years > 0:
            return f"I have {years} years of professional experience in the field."
        return "I am a recent graduate with strong academic projects and internship experience."
    
    def _generate_answer(self, question: str, profile: Dict[str, Any],
                         job: Dict[str, Any] = None) -> str:
        """Generate an answer using LLM.
        
        Args:
            question: The question
            profile: User profile
            job: Job context
            
        Returns:
            Generated answer
        """
        prompt = f"""Answer this job application question for the candidate:

**Question:** {question}

**Candidate Background:**
- Education: {profile.get('education', {}).get('degree', 'Computer Science')} in {profile.get('education', {}).get('specialization', 'Data Science')}
- Skills: {', '.join(profile.get('skills', {}).get('domains', [])[:5])}
- Experience: {profile.get('experience', {}).get('summary', 'Fresh graduate')}

{f"**Job Context:** {job.get('title', '')} at {job.get('company', '')}" if job else ""}

Provide a professional, honest, and concise answer (2-4 sentences max):"""

        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.6,
        )
        
        return answer.strip() if answer else "I would be happy to discuss this further."
    
    def answer_batch(self, questions: List[str], profile: Dict[str, Any],
                     job: Dict[str, Any] = None) -> Dict[str, str]:
        """Answer multiple questions.
        
        Args:
            questions: List of questions
            profile: User profile
            job: Job context
            
        Returns:
            Dictionary mapping questions to answers
        """
        return {q: self.answer_question(q, profile, job) for q in questions}
