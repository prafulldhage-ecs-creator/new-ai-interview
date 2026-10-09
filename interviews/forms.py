from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import InterviewSession, InterviewAnswer, InterviewQuestion


class InterviewSetupForm(forms.ModelForm):
    total_questions_target = forms.ChoiceField(
        choices=[(5, '5 Questions (Quick ~15 mins)'), (10, '10 Questions (Standard ~30 mins)'), (15, '15 Questions (Comprehensive ~45 mins)')],
        initial=5,
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'invalid_choice': 'Interview length must be 5, 10, or 15 questions.'}
    )

    class Meta:
        model = InterviewSession
        fields = [
            'title',
            'interview_type',
            'technical_domain',
            'difficulty',
            'experience_level',
            'total_questions_target',
            'communication_mode',
            'interview_language',
            'target_role',
            'skills',
            'project_description',
            'job_description',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Frontend Developer Mock Interview'
            }),
            'interview_type': forms.Select(attrs={'class': 'form-select'}),
            'technical_domain': forms.Select(attrs={'class': 'form-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'experience_level': forms.Select(attrs={'class': 'form-select'}),
            'communication_mode': forms.Select(attrs={'class': 'form-select'}),
            'interview_language': forms.Select(attrs={'class': 'form-select'}),
            'target_role': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. SDE 1, Graduate Trainee, Full Stack Intern'
            }),
            'skills': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Python, SQL, REST APIs, Git, Docker'
            }),
            'project_description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Briefly describe your major academic or personal projects (optional)...'
            }),
            'job_description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Paste job requirements or target company focus areas (optional)...'
            }),
        }

    def clean_total_questions_target(self):
        val = int(self.cleaned_data['total_questions_target'])
        if val not in [5, 10, 15]:
            raise forms.ValidationError("Interview length must be 5, 10, or 15 questions.")
        return val

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            return "Placement Mock Interview"
        return title[:200]


class AnswerSubmissionForm(forms.Form):
    question_id = forms.IntegerField(min_value=1)
    text = forms.CharField(
        widget=forms.Textarea,
        min_length=2,
        max_length=15000,
        error_messages={
            'required': 'Please provide an answer before submitting.',
            'min_length': 'Answer is too short. Please provide a substantive response.'
        }
    )
    input_method = forms.ChoiceField(
        choices=[('text', 'Text'), ('voice', 'Voice')],
        initial='text',
        required=False
    )
    duration_seconds = forms.IntegerField(min_value=0, required=False, initial=0)

    def clean_text(self):
        text = self.cleaned_data.get('text', '').strip()
        if not text:
            raise forms.ValidationError("Answer text cannot be empty or solely whitespace.")
        return text


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@college.edu'}))

    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose a username'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email
