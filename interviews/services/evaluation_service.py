"""
Evaluation Service - InterviewIQ
Handles evaluation aggregation, communication transcript analysis, and scoring rubrics.
"""

import re
from typing import Dict, List, Any


FILLER_WORDS = [
    'um', 'uh', 'er', 'ah', 'like', 'basically', 'actually', 'you know',
    'kind of', 'sort of', 'i mean', 'so yeah', 'right'
]


class EvaluationService:
    """
    Standard scoring rubric:
    1. Technical Correctness (40%)
    2. Conceptual Understanding & Depth (25%)
    3. Completeness & Missing Concepts (20%)
    4. Practical Application & Reasoning (15%)
    """

    RUBRIC_EXPLANATION = (
        "Scores are computed across four core dimensions: "
        "Technical Correctness (40%), Conceptual Depth (25%), Completeness (20%), "
        "and Practical Reasoning (15%). Subjective communication indicators are analyzed separately "
        "and do not unfairly penalize regional accents or thoughtful pauses."
    )

    @staticmethod
    def analyze_communication(text: str, duration_seconds: int = 0) -> Dict[str, Any]:
        """
        Analyzes the candidate's transcript for communication metrics:
        - Word count
        - Estimated speech pace (WPM)
        - Filler word occurrences
        - Vocabulary diversity
        """
        if not text:
            return {
                'word_count': 0,
                'filler_count': 0,
                'filler_ratio_pct': 0.0,
                'detected_fillers': [],
                'words_per_minute': 0,
                'clarity_level': 'Insufficient text'
            }

        cleaned_text = text.lower()
        words = re.findall(r'\b[a-zA-Z0-9_\'-]+\b', cleaned_text)
        word_count = len(words)

        if word_count == 0:
            return {
                'word_count': 0,
                'filler_count': 0,
                'filler_ratio_pct': 0.0,
                'detected_fillers': [],
                'words_per_minute': 0,
                'clarity_level': 'Empty'
            }

        detected_fillers = []
        filler_count = 0
        for filler in FILLER_WORDS:
            # Match word boundary
            matches = re.findall(r'\b' + re.escape(filler) + r'\b', cleaned_text)
            if matches:
                detected_fillers.append({'word': filler, 'count': len(matches)})
                filler_count += len(matches)

        filler_ratio = round((filler_count / word_count) * 100, 1) if word_count > 0 else 0.0

        wpm = 0
        if duration_seconds > 0:
            wpm = int((word_count / duration_seconds) * 60)

        # Clarity assessment
        if filler_ratio < 3.0 and word_count >= 20:
            clarity_level = 'Strong & Articulate'
        elif filler_ratio < 7.0:
            clarity_level = 'Clear & Understandable'
        else:
            clarity_level = 'Needs Reduction in Filler Words'

        return {
            'word_count': word_count,
            'filler_count': filler_count,
            'filler_ratio_pct': filler_ratio,
            'detected_fillers': detected_fillers,
            'words_per_minute': wpm,
            'clarity_level': clarity_level
        }

    @staticmethod
    def calculate_session_metrics(evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates session scores from answered evaluations.
        Never fabricates scores for unanswered questions.
        """
        if not evaluations:
            return {
                'overall_score': None,
                'scored_questions_count': 0,
                'rubric_explanation': EvaluationService.RUBRIC_EXPLANATION,
                'classification_breakdown': {},
                'strengths': [],
                'knowledge_gaps': [],
                'recommended_topics': []
            }

        total_score = sum(e.get('score', 0.0) for e in evaluations)
        count = len(evaluations)
        overall_score = round(total_score / count, 1)

        breakdown = {}
        all_correct_concepts = []
        all_missing_concepts = []
        all_incorrect_statements = []

        for e in evaluations:
            cls = e.get('classification', 'Partially correct')
            breakdown[cls] = breakdown.get(cls, 0) + 1

            for c in e.get('correct_concepts', []):
                if c and c not in all_correct_concepts:
                    all_correct_concepts.append(c)

            for m in e.get('missing_concepts', []):
                if m and m not in all_missing_concepts:
                    all_missing_concepts.append(m)

            for inc in e.get('incorrect_statements', []):
                if inc and inc not in all_incorrect_statements:
                    all_incorrect_statements.append(inc)

        # Construct actionable recommendations
        recommended_topics = all_missing_concepts[:5]

        return {
            'overall_score': overall_score,
            'scored_questions_count': count,
            'rubric_explanation': EvaluationService.RUBRIC_EXPLANATION,
            'classification_breakdown': breakdown,
            'strengths': all_correct_concepts[:6],
            'knowledge_gaps': all_missing_concepts[:6],
            'incorrect_statements': all_incorrect_statements[:5],
            'recommended_topics': recommended_topics
        }
