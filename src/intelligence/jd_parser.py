"""
Job Description Parser - Extract structured requirements from job descriptions.

Uses LLM for intelligent parsing of job requirements, skills, and qualifications.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

from ..llm import OllamaClient


class JDParser:
    """
    Parse job descriptions and extract structured requirements.
    
    Uses a combination of rule-based extraction and LLM analysis
    for comprehensive JD understanding.
    """
    
    # Common skill keywords to look for
    SKILL_PATTERNS = {
        "programming": [
            r'\bpython\b', r'\bjava\b', r'\bjavascript\b', r'\btypescript\b',
            r'\bc\+\+\b', r'\bc#\b', r'\bruby\b', r'\bgo\b', r'\brust\b',
            r'\bscala\b', r'\bkotlin\b', r'\bswift\b', r'\bphp\b', r'\br\b',
        ],
        "ml_ai": [
            r'machine\s*learning', r'deep\s*learning', r'\bml\b', r'\bdl\b',
            r'neural\s*network', r'\bnlp\b', r'natural\s*language',
            r'computer\s*vision', r'\bcv\b', r'tensorflow', r'pytorch',
            r'keras', r'scikit-learn', r'\bllm\b', r'transformer',
        ],
        "data": [
            r'data\s*science', r'data\s*analysis', r'data\s*engineering',
            r'\bsql\b', r'pandas', r'numpy', r'statistics', r'analytics',
            r'big\s*data', r'\betl\b', r'data\s*pipeline',
        ],
        "cloud": [
            r'\baws\b', r'\bgcp\b', r'google\s*cloud', r'\bazure\b',
            r'docker', r'kubernetes', r'\bk8s\b', r'terraform',
        ],
    }
    
    # Experience level patterns
    EXPERIENCE_PATTERNS = [
        (r'(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of)?\s*(?:experience|exp)', 'years'),
        (r'entry\s*level', 'entry'),
        (r'junior|jr\.?', 'junior'),
        (r'mid\s*level|mid-level', 'mid'),
        (r'senior|sr\.?', 'senior'),
        (r'lead|principal|staff', 'senior+'),
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize JD parser.
        
        Args:
            config: Configuration dictionary with LLM settings
        """
        self.config = config
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
    
    def parse(self, jd_text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Parse job description and extract requirements.
        
        Args:
            jd_text: Raw job description text
            use_llm: Whether to use LLM for enhanced parsing
            
        Returns:
            Structured dictionary with extracted requirements
        """
        # Clean the text
        jd_text = self._clean_text(jd_text)
        
        # Rule-based extraction
        result = {
            "raw_text": jd_text,
            "required_skills": self._extract_skills(jd_text),
            "nice_to_have_skills": [],
            "experience_level": self._extract_experience_level(jd_text),
            "experience_years": self._extract_experience_years(jd_text),
            "education": self._extract_education(jd_text),
            "responsibilities": [],
            "benefits": [],
            "work_mode": self._extract_work_mode(jd_text),
            "job_type": self._extract_job_type(jd_text),
        }
        
        # Enhanced parsing with LLM
        if use_llm and self.llm.is_available():
            llm_result = self._parse_with_llm(jd_text)
            if llm_result:
                result = self._merge_results(result, llm_result)
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize job description text."""
        # Remove HTML tags if present
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\-\@\+\(\)\/\&]', '', text)
        return text.strip()
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract required skills using pattern matching."""
        text_lower = text.lower()
        found_skills = set()
        
        for category, patterns in self.SKILL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    # Extract the actual matched skill
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        skill = match.group(0).strip()
                        found_skills.add(skill.title())
        
        return sorted(list(found_skills))
    
    def _extract_experience_level(self, text: str) -> str:
        """Extract experience level from job description."""
        text_lower = text.lower()
        
        for pattern, level in self.EXPERIENCE_PATTERNS[1:]:  # Skip years pattern
            if re.search(pattern, text_lower):
                return level
        
        # Infer from years if specified
        years = self._extract_experience_years(text)
        if years:
            if years <= 1:
                return "entry"
            elif years <= 3:
                return "junior"
            elif years <= 5:
                return "mid"
            else:
                return "senior"
        
        return "unknown"
    
    def _extract_experience_years(self, text: str) -> Optional[int]:
        """Extract required years of experience."""
        text_lower = text.lower()
        
        pattern = r'(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of)?\s*(?:experience|exp)'
        match = re.search(pattern, text_lower)
        
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_education(self, text: str) -> Dict[str, Any]:
        """Extract education requirements."""
        text_lower = text.lower()
        education = {
            "degree": None,
            "fields": [],
        }
        
        # Degree patterns
        degree_patterns = [
            (r"ph\.?d\.?|doctorate", "PhD"),
            (r"master'?s?|m\.?s\.?|m\.?tech", "Master's"),
            (r"bachelor'?s?|b\.?s\.?|b\.?tech|b\.?e\.?", "Bachelor's"),
        ]
        
        for pattern, degree in degree_patterns:
            if re.search(pattern, text_lower):
                education["degree"] = degree
                break
        
        # Field patterns
        field_patterns = [
            r'computer\s*science',
            r'data\s*science',
            r'machine\s*learning',
            r'artificial\s*intelligence',
            r'software\s*engineering',
            r'information\s*technology',
            r'mathematics',
            r'statistics',
            r'engineering',
        ]
        
        for pattern in field_patterns:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                education["fields"].append(match.group(0).title())
        
        return education
    
    def _extract_work_mode(self, text: str) -> str:
        """Extract work mode (remote, hybrid, onsite)."""
        text_lower = text.lower()
        
        if re.search(r'\bremote\b|\bwork\s*from\s*home\b|\bwfh\b', text_lower):
            if re.search(r'\bhybrid\b', text_lower):
                return "hybrid"
            return "remote"
        elif re.search(r'\bhybrid\b', text_lower):
            return "hybrid"
        elif re.search(r'\bon-?site\b|\bin-?office\b|\bin\s*person\b', text_lower):
            return "onsite"
        
        return "unknown"
    
    def _extract_job_type(self, text: str) -> str:
        """Extract job type (full-time, part-time, contract, internship)."""
        text_lower = text.lower()
        
        if re.search(r'\bintern(?:ship)?\b', text_lower):
            return "internship"
        elif re.search(r'\bcontract\b|\bfreelance\b', text_lower):
            return "contract"
        elif re.search(r'\bpart\s*-?\s*time\b', text_lower):
            return "part-time"
        elif re.search(r'\bfull\s*-?\s*time\b', text_lower):
            return "full-time"
        
        return "full-time"  # Default assumption
    
    def _parse_with_llm(self, jd_text: str) -> Optional[Dict[str, Any]]:
        """Use LLM for enhanced JD parsing."""
        prompt = f"""Analyze this job description and extract structured information.
Return ONLY a valid JSON object with these fields:
- required_skills: array of required technical skills
- nice_to_have_skills: array of optional/preferred skills
- responsibilities: array of key job responsibilities (max 5)
- benefits: array of mentioned benefits/perks (max 5)

Job Description:
{jd_text[:3000]}  # Limit to avoid token limits

Return only the JSON object, no other text."""

        try:
            response = self.llm.generate(prompt, temperature=0.1)
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
            
            return None
        except Exception as e:
            self.logger.warning(f"LLM parsing failed: {e}")
            return None
    
    def _merge_results(self, rule_based: Dict, llm_result: Dict) -> Dict[str, Any]:
        """Merge rule-based and LLM results."""
        merged = rule_based.copy()
        
        # Merge skills (combine and deduplicate)
        if "required_skills" in llm_result:
            all_skills = set(merged["required_skills"])
            all_skills.update(llm_result.get("required_skills", []))
            merged["required_skills"] = sorted(list(all_skills))
        
        # Take nice-to-have from LLM if available
        if "nice_to_have_skills" in llm_result:
            merged["nice_to_have_skills"] = llm_result["nice_to_have_skills"]
        
        # Take responsibilities from LLM
        if "responsibilities" in llm_result:
            merged["responsibilities"] = llm_result["responsibilities"]
        
        # Take benefits from LLM
        if "benefits" in llm_result:
            merged["benefits"] = llm_result["benefits"]
        
        return merged
    
    def get_skill_requirements(self, jd_text: str) -> Dict[str, List[str]]:
        """
        Get categorized skill requirements from JD.
        
        Args:
            jd_text: Job description text
            
        Returns:
            Dictionary with required and nice-to-have skills
        """
        parsed = self.parse(jd_text, use_llm=False)  # Quick extraction
        
        return {
            "required": parsed["required_skills"],
            "nice_to_have": parsed["nice_to_have_skills"],
        }
    
    def is_internship(self, jd_text: str) -> bool:
        """Check if the job is an internship."""
        return self._extract_job_type(jd_text) == "internship"
    
    def is_remote(self, jd_text: str) -> bool:
        """Check if the job is remote."""
        return self._extract_work_mode(jd_text) in ["remote", "hybrid"]


# Convenience function
def parse_job_description(jd_text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a job description and return structured data."""
    parser = JDParser(config)
    return parser.parse(jd_text)
