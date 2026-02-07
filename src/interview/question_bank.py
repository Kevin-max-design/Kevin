"""
Question Bank - Pre-built interview questions organized by topic and difficulty.

Provides a comprehensive library of interview questions for quick reference
when LLM is unavailable or for supplementing generated questions.
"""

from typing import Dict, Any, List, Optional


class QuestionBank:
    """
    Pre-built interview question library.
    
    Organized by:
    - Category (technical, behavioral, system design)
    - Topic (data structures, ML, SQL, etc.)
    - Difficulty (easy, medium, hard)
    """
    
    TECHNICAL_QUESTIONS = {
        "data_structures": [
            {
                "question": "Explain the difference between an array and a linked list.",
                "difficulty": "easy",
                "expected_answer": "Arrays offer O(1) random access but O(n) insertion/deletion. Linked lists offer O(1) insertion/deletion at known positions but O(n) access.",
                "topics": ["time complexity", "memory allocation", "use cases"],
            },
            {
                "question": "How would you implement a LRU cache?",
                "difficulty": "medium",
                "expected_answer": "Use a hash map for O(1) lookup combined with a doubly linked list for O(1) access order updates.",
                "topics": ["hash map", "doubly linked list", "cache eviction"],
            },
            {
                "question": "Explain how a hash table handles collisions.",
                "difficulty": "medium",
                "expected_answer": "Common approaches: chaining (linked lists at each bucket) or open addressing (linear/quadratic probing).",
                "topics": ["chaining", "open addressing", "load factor"],
            },
            {
                "question": "When would you use a tree vs a graph?",
                "difficulty": "easy",
                "expected_answer": "Trees are hierarchical with no cycles (file systems, DOM). Graphs handle complex relationships with potential cycles (social networks, maps).",
                "topics": ["hierarchy", "cycles", "traversal"],
            },
        ],
        "algorithms": [
            {
                "question": "Explain the difference between BFS and DFS.",
                "difficulty": "easy",
                "expected_answer": "BFS explores level by level (queue), good for shortest path. DFS goes deep first (stack/recursion), good for connectivity.",
                "topics": ["traversal", "queue vs stack", "use cases"],
            },
            {
                "question": "What is dynamic programming and when would you use it?",
                "difficulty": "medium",
                "expected_answer": "DP solves problems by breaking into overlapping subproblems and storing results. Used when problem has optimal substructure and overlapping subproblems.",
                "topics": ["memoization", "tabulation", "optimal substructure"],
            },
            {
                "question": "Explain time complexity of common sorting algorithms.",
                "difficulty": "medium",
                "expected_answer": "QuickSort: O(n log n) avg, O(n²) worst. MergeSort: O(n log n) guaranteed. HeapSort: O(n log n). Counting/Radix: O(n).",
                "topics": ["comparison sorts", "non-comparison sorts", "stability"],
            },
        ],
        "machine_learning": [
            {
                "question": "Explain the bias-variance tradeoff.",
                "difficulty": "medium",
                "expected_answer": "Bias: error from oversimplified model. Variance: error from model sensitivity to training data. Balance needed to minimize total error.",
                "topics": ["underfitting", "overfitting", "regularization"],
            },
            {
                "question": "How does gradient descent work?",
                "difficulty": "easy",
                "expected_answer": "Iteratively adjusts parameters in the direction of steepest descent of the loss function to find minimum.",
                "topics": ["learning rate", "convergence", "local minima"],
            },
            {
                "question": "Explain the difference between L1 and L2 regularization.",
                "difficulty": "medium",
                "expected_answer": "L1 (Lasso) promotes sparsity, can zero out features. L2 (Ridge) distributes weight across features. Choice depends on feature selection needs.",
                "topics": ["sparsity", "feature selection", "shrinkage"],
            },
            {
                "question": "What is cross-validation and why is it important?",
                "difficulty": "easy",
                "expected_answer": "Technique to assess model performance by training on subsets and validating on held-out data. Prevents overfitting to test set.",
                "topics": ["k-fold", "stratified", "data leakage"],
            },
            {
                "question": "Explain precision, recall, and F1 score.",
                "difficulty": "medium",
                "expected_answer": "Precision: TP/(TP+FP). Recall: TP/(TP+FN). F1: harmonic mean balancing both. Choice depends on cost of errors.",
                "topics": ["confusion matrix", "tradeoffs", "imbalanced data"],
            },
        ],
        "deep_learning": [
            {
                "question": "Explain backpropagation.",
                "difficulty": "medium",
                "expected_answer": "Algorithm to compute gradients by applying chain rule backwards through network layers, enabling weight updates.",
                "topics": ["chain rule", "gradients", "computational graph"],
            },
            {
                "question": "What is the vanishing gradient problem?",
                "difficulty": "medium",
                "expected_answer": "Gradients become very small in deep networks, preventing effective learning of early layers. Solutions: ReLU, residual connections, batch norm.",
                "topics": ["activation functions", "initialization", "architecture"],
            },
            {
                "question": "Explain how attention mechanism works in transformers.",
                "difficulty": "hard",
                "expected_answer": "Computes weighted sum of values based on query-key similarity. Allows modeling long-range dependencies without recurrence.",
                "topics": ["self-attention", "multi-head", "positional encoding"],
            },
        ],
        "sql": [
            {
                "question": "Explain different types of SQL joins.",
                "difficulty": "easy",
                "expected_answer": "INNER: matching rows only. LEFT: all from left + matches. RIGHT: all from right + matches. FULL: all rows from both.",
                "topics": ["join conditions", "NULL handling", "performance"],
            },
            {
                "question": "What are window functions and when would you use them?",
                "difficulty": "medium",
                "expected_answer": "Perform calculations across row sets without grouping. Used for running totals, rankings, moving averages.",
                "topics": ["PARTITION BY", "ORDER BY", "ROWS/RANGE"],
            },
            {
                "question": "How would you optimize a slow SQL query?",
                "difficulty": "medium",
                "expected_answer": "Check EXPLAIN plan, add indexes, avoid SELECT *, reduce subqueries, consider query restructuring.",
                "topics": ["indexes", "query plans", "normalization"],
            },
        ],
        "system_design": [
            {
                "question": "How would you design a URL shortener?",
                "difficulty": "medium",
                "expected_answer": "Generate unique short codes, store mapping in database, handle redirects, consider caching, analytics.",
                "topics": ["hashing", "database choice", "scalability"],
            },
            {
                "question": "Design a rate limiter.",
                "difficulty": "medium",
                "expected_answer": "Options: token bucket, leaky bucket, sliding window. Consider distributed systems, storage (Redis), graceful degradation.",
                "topics": ["algorithms", "distributed systems", "caching"],
            },
            {
                "question": "How would you design a recommendation system?",
                "difficulty": "hard",
                "expected_answer": "Approaches: collaborative filtering, content-based, hybrid. Consider cold start, scalability, A/B testing.",
                "topics": ["algorithms", "embedding", "real-time vs batch"],
            },
        ],
    }
    
    BEHAVIORAL_QUESTIONS = {
        "experience": [
            {
                "question": "Tell me about a project you're most proud of.",
                "category": "experience",
                "key_points": ["Technical challenge", "Your contribution", "Impact"],
            },
            {
                "question": "Describe a time when you had to learn a new technology quickly.",
                "category": "learning",
                "key_points": ["Approach to learning", "Resources used", "Application"],
            },
            {
                "question": "Tell me about a time you made a mistake at work.",
                "category": "resilience",
                "key_points": ["What happened", "How you resolved it", "What you learned"],
            },
        ],
        "teamwork": [
            {
                "question": "Describe a time when you disagreed with a team member.",
                "category": "conflict",
                "key_points": ["Situation", "How you handled it", "Resolution"],
            },
            {
                "question": "Tell me about a time you helped a colleague succeed.",
                "category": "collaboration",
                "key_points": ["Context", "Your support", "Outcome"],
            },
        ],
        "leadership": [
            {
                "question": "Describe a time when you took initiative.",
                "category": "initiative",
                "key_points": ["Situation", "Action taken", "Results"],
            },
            {
                "question": "Tell me about a time you had to convince others of your idea.",
                "category": "influence",
                "key_points": ["Your idea", "Approach", "Outcome"],
            },
        ],
    }
    
    def __init__(self):
        """Initialize question bank."""
        pass
    
    def get_questions_by_topic(
        self, 
        topic: str, 
        difficulty: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get questions for a specific topic.
        
        Args:
            topic: Topic name (e.g., 'machine_learning', 'sql')
            difficulty: Optional difficulty filter
            limit: Maximum questions to return
            
        Returns:
            List of questions
        """
        topic_key = topic.lower().replace(" ", "_").replace("-", "_")
        questions = self.TECHNICAL_QUESTIONS.get(topic_key, [])
        
        if difficulty:
            questions = [q for q in questions if q.get("difficulty") == difficulty]
        
        return questions[:limit]
    
    def get_behavioral_questions(
        self,
        category: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get behavioral/HR questions.
        
        Args:
            category: Optional category filter
            limit: Maximum questions to return
            
        Returns:
            List of questions
        """
        all_questions = []
        
        for cat, questions in self.BEHAVIORAL_QUESTIONS.items():
            if category is None or cat == category:
                for q in questions:
                    q["category"] = cat
                    all_questions.append(q)
        
        return all_questions[:limit]
    
    def get_difficulty_questions(
        self,
        difficulty: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get all questions of a specific difficulty.
        
        Args:
            difficulty: easy, medium, or hard
            limit: Maximum questions to return
            
        Returns:
            List of questions
        """
        questions = []
        
        for topic, topic_questions in self.TECHNICAL_QUESTIONS.items():
            for q in topic_questions:
                if q.get("difficulty") == difficulty:
                    q["topic"] = topic
                    questions.append(q)
        
        return questions[:limit]
    
    def search_questions(
        self,
        keywords: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search questions by keywords.
        
        Args:
            keywords: Keywords to search for
            limit: Maximum questions to return
            
        Returns:
            Matching questions
        """
        results = []
        keywords_lower = [k.lower() for k in keywords]
        
        for topic, questions in self.TECHNICAL_QUESTIONS.items():
            for q in questions:
                question_lower = q["question"].lower()
                if any(kw in question_lower for kw in keywords_lower):
                    q["topic"] = topic
                    results.append(q)
        
        for cat, questions in self.BEHAVIORAL_QUESTIONS.items():
            for q in questions:
                question_lower = q["question"].lower()
                if any(kw in question_lower for kw in keywords_lower):
                    q["category"] = cat
                    results.append(q)
        
        return results[:limit]
    
    def get_all_topics(self) -> List[str]:
        """Get list of all available topics."""
        return list(self.TECHNICAL_QUESTIONS.keys())
    
    def get_topic_summary(self) -> Dict[str, int]:
        """Get count of questions per topic."""
        return {
            topic: len(questions) 
            for topic, questions in self.TECHNICAL_QUESTIONS.items()
        }
