import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class InterviewSession(models.Model):
    # State Machine Definition
    STATE_CREATED = 'CREATED'
    STATE_READY = 'READY'
    STATE_ASKING = 'ASKING'
    STATE_WAITING_FOR_ANSWER = 'WAITING_FOR_ANSWER'
    STATE_EVALUATING = 'EVALUATING'
    STATE_FOLLOW_UP = 'FOLLOW_UP'
    STATE_COMPLETED = 'COMPLETED'
    STATE_CANCELLED = 'CANCELLED'
    STATE_ERROR = 'ERROR'

    STATE_CHOICES = [
        (STATE_CREATED, 'Created'),
        (STATE_READY, 'Ready'),
        (STATE_ASKING, 'Asking Question'),
        (STATE_WAITING_FOR_ANSWER, 'Waiting for Answer'),
        (STATE_EVALUATING, 'Evaluating Answer'),
        (STATE_FOLLOW_UP, 'Follow-up Question'),
        (STATE_COMPLETED, 'Completed'),
        (STATE_CANCELLED, 'Cancelled'),
        (STATE_ERROR, 'Error'),
    ]

    # Valid transitions from each state
    VALID_TRANSITIONS = {
        STATE_CREATED: {STATE_READY, STATE_CANCELLED, STATE_ERROR},
        STATE_READY: {STATE_ASKING, STATE_WAITING_FOR_ANSWER, STATE_CANCELLED, STATE_ERROR},
        STATE_ASKING: {STATE_WAITING_FOR_ANSWER, STATE_CANCELLED, STATE_ERROR},
        STATE_WAITING_FOR_ANSWER: {STATE_EVALUATING, STATE_CANCELLED, STATE_COMPLETED, STATE_ERROR},
        STATE_EVALUATING: {STATE_ASKING, STATE_WAITING_FOR_ANSWER, STATE_FOLLOW_UP, STATE_COMPLETED, STATE_CANCELLED, STATE_ERROR},
        STATE_FOLLOW_UP: {STATE_WAITING_FOR_ANSWER, STATE_CANCELLED, STATE_ERROR},
        STATE_COMPLETED: set(),
        STATE_CANCELLED: set(),
        STATE_ERROR: {STATE_READY, STATE_CANCELLED},
    }

    TYPE_TECHNICAL = 'Technical Interview'
    TYPE_HR = 'HR Interview'
    TYPE_PROJECT = 'Project-Based Interview'
    TYPE_MIXED = 'Mixed Interview'
    TYPE_COMMUNICATION = 'Communication Practice'

    TYPE_CHOICES = [
        (TYPE_TECHNICAL, 'Technical Interview'),
        (TYPE_HR, 'HR Interview'),
        (TYPE_PROJECT, 'Project-Based Interview'),
        (TYPE_MIXED, 'Mixed Interview'),
        (TYPE_COMMUNICATION, 'Communication Practice'),
    ]

    DOMAIN_HTML_CSS = 'HTML and CSS'
    DOMAIN_JAVASCRIPT = 'JavaScript'
    DOMAIN_REACT = 'React'
    DOMAIN_PYTHON = 'Python'
    DOMAIN_JAVA = 'Java'
    DOMAIN_CPP = 'C and C++'
    DOMAIN_DSA = 'Data Structures and Algorithms'
    DOMAIN_DBMS_SQL = 'DBMS and SQL'
    DOMAIN_OS = 'Operating Systems'
    DOMAIN_NETWORKS = 'Computer Networks'
    DOMAIN_OOP = 'Object-Oriented Programming'
    DOMAIN_AIML = 'AI and Machine Learning'
    DOMAIN_SE = 'Software Engineering'

    DOMAIN_CHOICES = [
        (DOMAIN_HTML_CSS, 'HTML and CSS'),
        (DOMAIN_JAVASCRIPT, 'JavaScript'),
        (DOMAIN_REACT, 'React'),
        (DOMAIN_PYTHON, 'Python'),
        (DOMAIN_JAVA, 'Java'),
        (DOMAIN_CPP, 'C and C++'),
        (DOMAIN_DSA, 'Data Structures and Algorithms'),
        (DOMAIN_DBMS_SQL, 'DBMS and SQL'),
        (DOMAIN_OS, 'Operating Systems'),
        (DOMAIN_NETWORKS, 'Computer Networks'),
        (DOMAIN_OOP, 'Object-Oriented Programming'),
        (DOMAIN_AIML, 'AI and Machine Learning'),
        (DOMAIN_SE, 'Software Engineering'),
    ]

    DIFF_EASY = 'Easy'
    DIFF_MEDIUM = 'Medium'
    DIFF_HARD = 'Hard'
    DIFF_ADAPTIVE = 'Adaptive'

    DIFFICULTY_CHOICES = [
        (DIFF_EASY, 'Easy'),
        (DIFF_MEDIUM, 'Medium'),
        (DIFF_HARD, 'Hard'),
        (DIFF_ADAPTIVE, 'Adaptive'),
    ]

    EXP_INTERNSHIP = 'Internship'
    EXP_FRESHER = 'Fresher'
    EXP_ENTRY = 'Entry-Level Developer'

    EXPERIENCE_CHOICES = [
        (EXP_INTERNSHIP, 'Internship'),
        (EXP_FRESHER, 'Fresher'),
        (EXP_ENTRY, 'Entry-Level Developer'),
    ]

    MODE_TEXT = 'Text'
    MODE_VOICE = 'Voice'

    MODE_CHOICES = [
        (MODE_TEXT, 'Text'),
        (MODE_VOICE, 'Voice (Speech-to-Text)'),
    ]

    LANG_ENGLISH = 'English'
    LANG_HINDI = 'Hindi'
    LANG_MARATHI = 'Marathi'

    LANGUAGE_CHOICES = [
        (LANG_ENGLISH, 'English'),
        (LANG_HINDI, 'Hindi'),
        (LANG_MARATHI, 'Marathi'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='interviews')
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    title = models.CharField(max_length=200, default='New Placement Interview')

    interview_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default=TYPE_TECHNICAL)
    technical_domain = models.CharField(max_length=100, choices=DOMAIN_CHOICES, default=DOMAIN_DSA)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default=DIFF_MEDIUM)
    current_difficulty = models.CharField(max_length=20, default=DIFF_MEDIUM)
    experience_level = models.CharField(max_length=30, choices=EXPERIENCE_CHOICES, default=EXP_FRESHER)
    total_questions_target = models.PositiveSmallIntegerField(default=5)
    communication_mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_TEXT)
    interview_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default=LANG_ENGLISH)

    # Optional context
    job_description = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    project_description = models.TextField(blank=True)
    target_role = models.CharField(max_length=150, blank=True)

    # State & Audit
    state = models.CharField(max_length=30, choices=STATE_CHOICES, default=STATE_CREATED, db_index=True)
    ai_mode_used = models.CharField(max_length=50, default='demo')
    overall_score = models.FloatField(null=True, blank=True)
    summary_report = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.interview_type} - {self.technical_domain} ({self.id})"

    def can_transition_to(self, new_state: str) -> bool:
        """Validate state transition against state machine rules."""
        if new_state == self.state:
            return True
        return new_state in self.VALID_TRANSITIONS.get(self.state, set())

    def transition_to(self, new_state: str, save: bool = True):
        """Transition to new state or raise ValueError if invalid."""
        if not self.can_transition_to(new_state):
            raise ValueError(f"Invalid state transition from '{self.state}' to '{new_state}'.")
        self.state = new_state
        if new_state == self.STATE_COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        if save:
            self.save()

    def current_question(self):
        """Get the latest question asked in this session."""
        return self.questions.order_by('-question_index', '-id').first()

    def completed_questions_count(self):
        """Count questions that have been evaluated."""
        return self.questions.filter(answer__evaluation__isnull=False).count()

    def is_finished(self):
        return self.state in (self.STATE_COMPLETED, self.STATE_CANCELLED)


class InterviewQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    question_index = models.PositiveIntegerField(default=1)
    is_follow_up = models.BooleanField(default=False)
    parent_question = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='follow_ups'
    )
    text = models.TextField()
    category = models.CharField(max_length=100, default='Technical')
    target_concept = models.CharField(max_length=200, blank=True)
    difficulty = models.CharField(max_length=30, default='Medium')
    interviewer_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question_index', 'id']

    def __str__(self):
        prefix = "Follow-up" if self.is_follow_up else f"Q{self.question_index}"
        return f"{prefix}: {self.text[:50]}..."

    @property
    def has_answer(self):
        return hasattr(self, 'answer')


class InterviewAnswer(models.Model):
    question = models.OneToOneField(InterviewQuestion, on_delete=models.CASCADE, related_name='answer')
    text = models.TextField()
    input_method = models.CharField(max_length=20, default='text')  # text or voice
    duration_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer for Q{self.question.question_index}: {self.text[:40]}..."


class InterviewEvaluation(models.Model):
    CLASS_CORRECT = 'Correct'
    CLASS_MOSTLY_CORRECT = 'Mostly correct'
    CLASS_PARTIALLY_CORRECT = 'Partially correct'
    CLASS_INCORRECT = 'Incorrect'
    CLASS_VAGUE = 'Vague'
    CLASS_OFF_TOPIC = 'Off-topic'
    CLASS_NEEDS_CLARIFICATION = 'Needs clarification'
    CLASS_UNABLE_TO_EVALUATE = 'Unable to evaluate'

    CLASSIFICATION_CHOICES = [
        (CLASS_CORRECT, 'Correct'),
        (CLASS_MOSTLY_CORRECT, 'Mostly correct'),
        (CLASS_PARTIALLY_CORRECT, 'Partially correct'),
        (CLASS_INCORRECT, 'Incorrect'),
        (CLASS_VAGUE, 'Vague'),
        (CLASS_OFF_TOPIC, 'Off-topic'),
        (CLASS_NEEDS_CLARIFICATION, 'Needs clarification'),
        (CLASS_UNABLE_TO_EVALUATE, 'Unable to evaluate'),
    ]

    answer = models.OneToOneField(InterviewAnswer, on_delete=models.CASCADE, related_name='evaluation')
    score = models.FloatField(default=0.0)  # 0 to 100
    classification = models.CharField(max_length=50, choices=CLASSIFICATION_CHOICES, default=CLASS_PARTIALLY_CORRECT)
    correct_concepts = models.JSONField(default=list, blank=True)
    missing_concepts = models.JSONField(default=list, blank=True)
    incorrect_statements = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    better_answer_example = models.TextField(blank=True)
    interviewer_response = models.TextField(blank=True)
    suggested_follow_up = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.95)
    communication_feedback = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation [{self.classification}]: {self.score}/100"
