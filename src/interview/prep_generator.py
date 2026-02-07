"""
Interview Prep Generator - Generate customized interview preparation materials.

Creates technical questions, HR questions, model answers, and study plans
based on job requirements and user profile.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..llm import OllamaClient
from ..database import InterviewPrep


class InterviewPrepGenerator:
    """
    Generate comprehensive interview preparation materials.
    
    Features:
    - Topic prediction based on JD
    - Technical question generation
    - HR/behavioral question preparation
    - Model answer generation
    - Daily study plan creation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize interview prep generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.llm = OllamaClient(config)
        self.logger = logging.getLogger(__name__)
    
    def generate_prep(
        self,
        job: Dict[str, Any],
        profile: Dict[str, Any],
        days_until_interview: int = 7,
    ) -> Dict[str, Any]:
        """
        Generate complete interview preparation materials.
        
        Args:
            job: Job data with description and requirements
            profile: User profile
            days_until_interview: Number of days to prepare
            
        Returns:
            Complete interview prep materials
        """
        self.logger.info(f"Generating interview prep for {job.get('title')} at {job.get('company')}")
        
        # Generate all components
        topics = self.predict_topics(job)
        technical_questions = self.generate_technical_questions(job, profile, topics)
        hr_questions = self.generate_hr_questions(job)
        model_answers = self.generate_model_answers(technical_questions, profile)
        prep_plan = self.create_study_plan(topics, days_until_interview)
        
        return {
            "job_id": job.get("id"),
            "job_title": job.get("title"),
            "company": job.get("company"),
            "predicted_topics": topics,
            "technical_questions": technical_questions,
            "hr_questions": hr_questions,
            "model_answers": model_answers,
            "prep_plan": prep_plan,
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def predict_topics(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Predict interview topics based on job description.
        
        Args:
            job: Job data
            
        Returns:
            List of predicted topics with importance levels
        """
        jd = job.get("description", "")
        title = job.get("title", "")
        required_skills = job.get("matched_skills", [])
        
        prompt = f"""Analyze this job posting and predict the main technical interview topics.

JOB TITLE: {title}
COMPANY: {job.get('company', '')}

JOB DESCRIPTION:
{jd[:2000]}

REQUIRED SKILLS: {', '.join(required_skills[:10]) if required_skills else 'Not specified'}

Return a JSON array of interview topics with this format:
[
    {{"topic": "Topic Name", "importance": "high/medium/low", "subtopics": ["subtopic1", "subtopic2"]}},
    ...
]

Include 5-8 main topics covering:
- Core technical skills mentioned
- Common interview topics for this role
- Company-relevant technologies

Return ONLY the JSON array, no other text."""

        try:
            if self.llm.is_available():
                response = self.llm.generate(prompt, temperature=0.3)
                json_match = self._extract_json_array(response)
                if json_match:
                    return json.loads(json_match)
            
            # Fallback to default topics
            return self._default_topics(title, required_skills)
        except Exception as e:
            self.logger.error(f"Topic prediction failed: {e}")
            return self._default_topics(title, required_skills)
    
    def generate_technical_questions(
        self,
        job: Dict[str, Any],
        profile: Dict[str, Any],
        topics: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate technical interview questions.
        
        Args:
            job: Job data
            profile: User profile
            topics: Predicted topics
            
        Returns:
            List of questions with difficulty and hints
        """
        topic_names = [t["topic"] for t in topics[:5]]
        
        prompt = f"""Generate technical interview questions for a {job.get('title', 'Software')} position.

TOPICS TO COVER: {', '.join(topic_names)}

CANDIDATE SKILLS: {', '.join(profile.get('skills', {}).get('programming', [])[:8])}

Generate 10 technical interview questions with this JSON format:
[
    {{
        "question": "The question text",
        "topic": "Related topic",
        "difficulty": "easy/medium/hard",
        "hint": "A brief hint",
        "expected_concepts": ["concept1", "concept2"]
    }},
    ...
]

Include a mix of:
- Conceptual questions (3-4)
- Problem-solving questions (3-4)
- System design or practical questions (2-3)

Return ONLY the JSON array."""

        try:
            if self.llm.is_available():
                response = self.llm.generate(prompt, temperature=0.5)
                json_match = self._extract_json_array(response)
                if json_match:
                    return json.loads(json_match)
            
            return self._default_technical_questions(topic_names)
        except Exception as e:
            self.logger.error(f"Technical question generation failed: {e}")
            return self._default_technical_questions(topic_names)
    
    def generate_hr_questions(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate HR/behavioral interview questions.
        
        Args:
            job: Job data
            
        Returns:
            List of HR questions with sample answer frameworks
        """
        prompt = f"""Generate behavioral/HR interview questions for a {job.get('title', '')} position at {job.get('company', 'a company')}.

Generate 8 common HR interview questions with this JSON format:
[
    {{
        "question": "The question text",
        "category": "motivation/teamwork/conflict/leadership/weakness/career",
        "answer_framework": "STAR or other framework suggestion",
        "key_points": ["point1", "point2"]
    }},
    ...
]

Include questions about:
- Motivation for this role
- Team collaboration
- Handling challenges
- Career goals
- Strengths and weaknesses

Return ONLY the JSON array."""

        try:
            if self.llm.is_available():
                response = self.llm.generate(prompt, temperature=0.4)
                json_match = self._extract_json_array(response)
                if json_match:
                    return json.loads(json_match)
            
            return self._default_hr_questions()
        except Exception as e:
            self.logger.error(f"HR question generation failed: {e}")
            return self._default_hr_questions()
    
    def generate_model_answers(
        self,
        questions: List[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Generate model answers for technical questions.
        
        Args:
            questions: List of questions
            profile: User profile for personalization
            
        Returns:
            Dictionary mapping question to model answer
        """
        model_answers = {}
        
        for q in questions[:5]:  # Limit to first 5 to avoid overloading
            question = q.get("question", "")
            
            prompt = f"""Provide a concise but comprehensive answer to this interview question:

QUESTION: {question}

CONTEXT:
- Topic: {q.get('topic', 'General')}
- Difficulty: {q.get('difficulty', 'medium')}
- Expected concepts: {', '.join(q.get('expected_concepts', []))}

Provide a clear, structured answer that:
1. Directly addresses the question
2. Includes relevant examples or code snippets if applicable
3. Demonstrates depth of knowledge
4. Is concise (3-5 paragraphs max)

Give only the answer, no preamble."""

            try:
                if self.llm.is_available():
                    answer = self.llm.generate(prompt, temperature=0.4)
                    model_answers[question] = answer.strip()
            except Exception as e:
                self.logger.error(f"Model answer generation failed: {e}")
        
        return model_answers
    
    def create_study_plan(
        self,
        topics: List[Dict[str, Any]],
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Create a day-by-day study plan.
        
        Args:
            topics: Topics to cover
            days: Number of days to prepare
            
        Returns:
            Study plan dictionary
        """
        # Sort topics by importance
        importance_order = {"high": 0, "medium": 1, "low": 2}
        sorted_topics = sorted(
            topics, 
            key=lambda x: importance_order.get(x.get("importance", "medium"), 1)
        )
        
        plan = {
            "total_days": days,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=days-1)).strftime("%Y-%m-%d"),
            "days": [],
        }
        
        # Distribute topics across days
        topics_per_day = max(1, len(sorted_topics) // days)
        
        for day in range(days):
            day_plan = {
                "day": day + 1,
                "date": (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d"),
                "topics": [],
                "exercises": [],
                "time_estimate": "2-3 hours",
            }
            
            # Assign topics for this day
            start_idx = day * topics_per_day
            day_topics = sorted_topics[start_idx:start_idx + topics_per_day + 1]
            
            for topic in day_topics:
                day_plan["topics"].append({
                    "name": topic.get("topic"),
                    "subtopics": topic.get("subtopics", []),
                    "importance": topic.get("importance"),
                })
            
            # Add exercise suggestions
            if day_topics:
                day_plan["exercises"] = [
                    f"Review {day_topics[0].get('topic', 'topic')} fundamentals",
                    "Practice related coding problems",
                    "Review past project examples",
                ]
            
            # Last day for mock interview
            if day == days - 1:
                day_plan["topics"].append({
                    "name": "Mock Interview & Review",
                    "subtopics": ["Practice with a friend", "Review weak areas", "Prepare questions for interviewer"],
                    "importance": "high",
                })
            
            plan["days"].append(day_plan)
        
        return plan
    
    def _extract_json_array(self, text: str) -> Optional[str]:
        """Extract JSON array from LLM response."""
        import re
        match = re.search(r'\[[\s\S]*\]', text)
        return match.group(0) if match else None
    
    def _default_topics(self, title: str, skills: List[str]) -> List[Dict[str, Any]]:
        """Generate default topics based on title and skills."""
        title_lower = title.lower()
        
        topics = []
        
        # Core topics based on role
        if "data" in title_lower or "scientist" in title_lower:
            topics.extend([
                {"topic": "Statistics & Probability", "importance": "high", "subtopics": ["Distributions", "Hypothesis testing", "A/B testing"]},
                {"topic": "Machine Learning", "importance": "high", "subtopics": ["Algorithms", "Model evaluation", "Feature engineering"]},
                {"topic": "SQL & Data Manipulation", "importance": "high", "subtopics": ["Joins", "Window functions", "Optimization"]},
            ])
        elif "machine learning" in title_lower or "ml" in title_lower:
            topics.extend([
                {"topic": "Deep Learning", "importance": "high", "subtopics": ["Neural networks", "CNNs", "RNNs", "Transformers"]},
                {"topic": "ML System Design", "importance": "high", "subtopics": ["Pipeline design", "Model serving", "Monitoring"]},
                {"topic": "Mathematics for ML", "importance": "medium", "subtopics": ["Linear algebra", "Calculus", "Probability"]},
            ])
        else:
            topics.extend([
                {"topic": "Data Structures", "importance": "high", "subtopics": ["Arrays", "Trees", "Graphs", "Hash tables"]},
                {"topic": "Algorithms", "importance": "high", "subtopics": ["Sorting", "Searching", "Dynamic programming"]},
                {"topic": "System Design", "importance": "medium", "subtopics": ["Scalability", "Databases", "Caching"]},
            ])
        
        # Add skill-based topics
        for skill in skills[:3]:
            topics.append({
                "topic": skill,
                "importance": "medium",
                "subtopics": [f"{skill} fundamentals", f"{skill} best practices"],
            })
        
        return topics
    
    def _default_technical_questions(self, topics: List[str]) -> List[Dict[str, Any]]:
        """Generate default technical questions."""
        questions = [
            {
                "question": "Explain the difference between supervised and unsupervised learning.",
                "topic": "Machine Learning",
                "difficulty": "easy",
                "hint": "Think about labeled vs unlabeled data",
                "expected_concepts": ["classification", "clustering", "regression"],
            },
            {
                "question": "How would you handle missing data in a dataset?",
                "topic": "Data Processing",
                "difficulty": "medium",
                "hint": "Consider different imputation strategies",
                "expected_concepts": ["imputation", "deletion", "domain knowledge"],
            },
            {
                "question": "Explain the bias-variance tradeoff.",
                "topic": "Machine Learning",
                "difficulty": "medium",
                "hint": "Think about model complexity",
                "expected_concepts": ["overfitting", "underfitting", "generalization"],
            },
        ]
        
        for topic in topics[:2]:
            questions.append({
                "question": f"Explain key concepts in {topic}.",
                "topic": topic,
                "difficulty": "medium",
                "hint": "Cover fundamentals and practical applications",
                "expected_concepts": [],
            })
        
        return questions
    
    def _default_hr_questions(self) -> List[Dict[str, Any]]:
        """Generate default HR questions."""
        return [
            {
                "question": "Tell me about yourself.",
                "category": "introduction",
                "answer_framework": "Present-Past-Future",
                "key_points": ["Current role/situation", "Relevant experience", "Career goals"],
            },
            {
                "question": "Why are you interested in this role?",
                "category": "motivation",
                "answer_framework": "Company + Role + Value",
                "key_points": ["Company research", "Role alignment", "Value you bring"],
            },
            {
                "question": "Tell me about a challenging project you worked on.",
                "category": "experience",
                "answer_framework": "STAR (Situation, Task, Action, Result)",
                "key_points": ["Context", "Your specific contribution", "Quantifiable outcome"],
            },
            {
                "question": "How do you handle disagreements with team members?",
                "category": "teamwork",
                "answer_framework": "STAR",
                "key_points": ["Active listening", "Finding common ground", "Professional resolution"],
            },
            {
                "question": "What are your strengths and weaknesses?",
                "category": "self-awareness",
                "answer_framework": "Strength + Evidence, Weakness + Improvement",
                "key_points": ["Relevant strength", "Genuine weakness", "Growth mindset"],
            },
            {
                "question": "Where do you see yourself in 5 years?",
                "category": "career",
                "answer_framework": "Growth + Impact",
                "key_points": ["Realistic goals", "Alignment with role", "Continuous learning"],
            },
        ]
