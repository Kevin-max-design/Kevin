"""
Semantic Matcher - Vector embedding-based job-resume matching.

Uses sentence transformers for semantic similarity matching between
resumes and job descriptions, providing more accurate matching than
keyword-based approaches.
"""

import json
import logging
import pickle
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class SemanticMatcher:
    """
    Semantic matching engine using vector embeddings.
    
    Provides:
    - Text to embedding conversion
    - Cosine similarity calculation
    - Resume-JD matching with detailed scoring
    - Skill gap analysis
    """
    
    # Default model - lightweight but effective
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(self, model_name: str = None):
        """
        Initialize the semantic matcher.
        
        Args:
            model_name: Name of the sentence-transformer model to use
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
    
    @property
    def model(self) -> Optional['SentenceTransformer']:
        """Lazy load the model."""
        if self._model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self.logger.info("Model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load model: {e}")
                return None
        return self._model
    
    def is_available(self) -> bool:
        """Check if semantic matching is available."""
        return SENTENCE_TRANSFORMERS_AVAILABLE and self.model is not None
    
    def encode(self, text: str, normalize: bool = True) -> Optional[np.ndarray]:
        """
        Encode text to embedding vector.
        
        Args:
            text: Text to encode
            normalize: Whether to normalize the embedding
            
        Returns:
            Numpy array embedding or None if unavailable
        """
        if not self.is_available():
            return None
        
        try:
            embedding = self.model.encode(
                text, 
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            return embedding
        except Exception as e:
            self.logger.error(f"Encoding failed: {e}")
            return None
    
    def encode_batch(self, texts: List[str], normalize: bool = True) -> Optional[np.ndarray]:
        """
        Encode multiple texts to embeddings.
        
        Args:
            texts: List of texts to encode
            normalize: Whether to normalize embeddings
            
        Returns:
            2D numpy array of embeddings
        """
        if not self.is_available():
            return None
        
        try:
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                batch_size=32
            )
            return embeddings
        except Exception as e:
            self.logger.error(f"Batch encoding failed: {e}")
            return None
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0 to 1)
        """
        emb1 = self.encode(text1)
        emb2 = self.encode(text2)
        
        if emb1 is None or emb2 is None:
            return 0.0
        
        return float(np.dot(emb1, emb2))
    
    def similarity_from_embeddings(
        self, 
        emb1: np.ndarray, 
        emb2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two pre-computed embeddings.
        
        Args:
            emb1: First embedding
            emb2: Second embedding
            
        Returns:
            Similarity score (0 to 1)
        """
        return float(np.dot(emb1, emb2))
    
    def match_resume_to_job(
        self, 
        resume_text: str, 
        job_description: str,
        resume_skills: List[str] = None,
        job_skills: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Match resume against job description with detailed scoring.
        
        Args:
            resume_text: Full resume text
            job_description: Full job description text
            resume_skills: Pre-extracted resume skills (optional)
            job_skills: Pre-extracted job skills (optional)
            
        Returns:
            Matching results with scores and analysis
        """
        result = {
            "overall_score": 0.0,
            "semantic_score": 0.0,
            "skill_score": 0.0,
            "matching_skills": [],
            "missing_skills": [],
            "skill_details": [],
        }
        
        # Calculate semantic similarity
        semantic_sim = self.similarity(resume_text, job_description)
        result["semantic_score"] = semantic_sim * 100
        
        # Skill matching if skills are provided
        if resume_skills and job_skills:
            skill_result = self.match_skills(resume_skills, job_skills)
            result["skill_score"] = skill_result["score"]
            result["matching_skills"] = skill_result["matching"]
            result["missing_skills"] = skill_result["missing"]
            result["skill_details"] = skill_result["details"]
            
            # Combined score (weighted average)
            result["overall_score"] = (
                0.4 * result["semantic_score"] + 
                0.6 * result["skill_score"]
            )
        else:
            result["overall_score"] = result["semantic_score"]
        
        return result
    
    def match_skills(
        self, 
        resume_skills: List[str], 
        job_skills: List[str],
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Match skills between resume and job with semantic similarity.
        
        Args:
            resume_skills: Skills from resume
            job_skills: Required skills from job
            threshold: Similarity threshold for considering a match
            
        Returns:
            Skill matching results
        """
        if not resume_skills or not job_skills:
            return {
                "score": 0.0,
                "matching": [],
                "missing": job_skills or [],
                "details": [],
            }
        
        matching = []
        missing = []
        details = []
        
        # Normalize skills for comparison
        resume_skills_lower = [s.lower() for s in resume_skills]
        
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            
            # First try exact match
            if job_skill_lower in resume_skills_lower:
                matching.append(job_skill)
                details.append({
                    "skill": job_skill,
                    "match_type": "exact",
                    "score": 1.0,
                    "matched_with": job_skill
                })
                continue
            
            # Then try semantic similarity
            if self.is_available():
                best_score = 0.0
                best_match = None
                
                for resume_skill in resume_skills:
                    sim = self.similarity(job_skill, resume_skill)
                    if sim > best_score:
                        best_score = sim
                        best_match = resume_skill
                
                if best_score >= threshold:
                    matching.append(job_skill)
                    details.append({
                        "skill": job_skill,
                        "match_type": "semantic",
                        "score": best_score,
                        "matched_with": best_match
                    })
                else:
                    missing.append(job_skill)
                    details.append({
                        "skill": job_skill,
                        "match_type": "missing",
                        "score": best_score,
                        "closest": best_match
                    })
            else:
                # Fallback to fuzzy string matching
                from difflib import SequenceMatcher
                
                best_score = 0.0
                best_match = None
                
                for resume_skill in resume_skills:
                    score = SequenceMatcher(
                        None, 
                        job_skill_lower, 
                        resume_skill.lower()
                    ).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = resume_skill
                
                if best_score >= threshold:
                    matching.append(job_skill)
                    details.append({
                        "skill": job_skill,
                        "match_type": "fuzzy",
                        "score": best_score,
                        "matched_with": best_match
                    })
                else:
                    missing.append(job_skill)
        
        # Calculate overall skill score
        if job_skills:
            score = (len(matching) / len(job_skills)) * 100
        else:
            score = 100.0
        
        return {
            "score": score,
            "matching": matching,
            "missing": missing,
            "details": details,
        }
    
    def find_best_resume(
        self, 
        job_description: str,
        resumes: List[Dict[str, Any]],
        job_skills: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Find the best matching resume for a job from a list.
        
        Args:
            job_description: Job description text
            resumes: List of resume dictionaries with 'text' and 'skills'
            job_skills: Required skills from job (optional)
            
        Returns:
            Best matching resume with score
        """
        if not resumes:
            return None
        
        best_match = None
        best_score = -1
        all_matches = []
        
        for resume in resumes:
            result = self.match_resume_to_job(
                resume.get("raw_text", ""),
                job_description,
                resume.get("skills", []),
                job_skills,
            )
            
            match_info = {
                "resume": resume,
                "score": result["overall_score"],
                "details": result,
            }
            all_matches.append(match_info)
            
            if result["overall_score"] > best_score:
                best_score = result["overall_score"]
                best_match = match_info
        
        return {
            "best_match": best_match,
            "all_matches": sorted(all_matches, key=lambda x: x["score"], reverse=True),
        }
    
    def embedding_to_bytes(self, embedding: np.ndarray) -> bytes:
        """Convert embedding to bytes for database storage."""
        return pickle.dumps(embedding)
    
    def bytes_to_embedding(self, data: bytes) -> np.ndarray:
        """Convert bytes back to embedding array."""
        return pickle.loads(data)
    
    def get_embedding_for_storage(self, text: str) -> Optional[bytes]:
        """Get embedding as bytes for database storage."""
        embedding = self.encode(text)
        if embedding is not None:
            return self.embedding_to_bytes(embedding)
        return None


class FallbackMatcher:
    """
    Fallback matcher when sentence-transformers is not available.
    Uses TF-IDF and fuzzy string matching.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def match_resume_to_job(
        self, 
        resume_text: str, 
        job_description: str,
        resume_skills: List[str] = None,
        job_skills: List[str] = None,
    ) -> Dict[str, Any]:
        """Basic matching using word overlap."""
        semantic_sim = self.similarity(resume_text, job_description)
        
        result = {
            "overall_score": semantic_sim * 100,
            "semantic_score": semantic_sim * 100,
            "skill_score": 0.0,
            "matching_skills": [],
            "missing_skills": [],
        }
        
        if resume_skills and job_skills:
            resume_lower = {s.lower() for s in resume_skills}
            matching = [s for s in job_skills if s.lower() in resume_lower]
            missing = [s for s in job_skills if s.lower() not in resume_lower]
            
            result["matching_skills"] = matching
            result["missing_skills"] = missing
            result["skill_score"] = (len(matching) / len(job_skills)) * 100 if job_skills else 0
            result["overall_score"] = (result["semantic_score"] + result["skill_score"]) / 2
        
        return result


def get_matcher(model_name: str = None) -> SemanticMatcher:
    """Get a semantic matcher instance."""
    matcher = SemanticMatcher(model_name)
    if not matcher.is_available():
        logging.warning("Using fallback matcher - install sentence-transformers for better results")
    return matcher
