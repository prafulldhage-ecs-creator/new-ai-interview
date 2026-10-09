from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from interviews.models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewEvaluation
from interviews.services.interview_engine import InterviewEngine


class InterviewViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teststudent', password='Password123!', email='student@test.edu')

    def test_homepage_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'InterviewIQ')
        self.assertContains(response, 'Simulate Real Technical')

    def test_dashboard_empty_state_and_loaded(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Candidate Dashboard')
        self.assertContains(response, 'No interviews completed yet')

    def test_interview_setup_get(self):
        response = self.client.get(reverse('interview_setup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configure Mock Interview')

    def test_interview_setup_post_valid(self):
        self.client.login(username='teststudent', password='Password123!')
        data = {
            'title': 'Python Backend Practice',
            'interview_type': 'Technical Interview',
            'technical_domain': 'Python',
            'difficulty': 'Medium',
            'experience_level': 'Fresher',
            'total_questions_target': 5,
            'communication_mode': 'Text',
            'interview_language': 'English',
            'target_role': 'Python Developer',
            'skills': 'Python, Django, SQL',
            'project_description': '',
            'job_description': '',
        }
        response = self.client.post(reverse('interview_setup'), data=data)
        self.assertEqual(response.status_code, 302)
        session = InterviewSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.technical_domain, 'Python')
        self.assertEqual(session.questions.count(), 1)
        self.assertEqual(session.state, InterviewSession.STATE_WAITING_FOR_ANSWER)

    def test_interview_setup_post_invalid_fields(self):
        # Invalid question count
        data = {
            'title': 'Test',
            'interview_type': 'Technical Interview',
            'technical_domain': 'Python',
            'difficulty': 'Medium',
            'experience_level': 'Fresher',
            'total_questions_target': 99,  # Invalid
            'communication_mode': 'Text',
            'interview_language': 'English',
        }
        response = self.client.post(reverse('interview_setup'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'total_questions_target', 'Interview length must be 5, 10, or 15 questions.')

    def test_room_view_access_and_security(self):
        session = InterviewSession.objects.create(
            user=self.user,
            title='Authorized Session',
            technical_domain='Data Structures and Algorithms',
            total_questions_target=5
        )
        InterviewEngine.start_session(session)

        # Another unauthenticated client cannot access it
        stranger_client = Client()
        response = stranger_client.get(reverse('interview_room', args=[session.id]))
        self.assertEqual(response.status_code, 403)

        # Owner can access it
        self.client.login(username='teststudent', password='Password123!')
        response = self.client.get(reverse('interview_room', args=[session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Interview Room')
        self.assertContains(response, 'Authorized Session')

    def test_api_submit_answer_and_progression(self):
        self.client.login(username='teststudent', password='Password123!')
        session = InterviewSession.objects.create(
            user=self.user,
            title='DSA Mock',
            technical_domain='Data Structures and Algorithms',
            total_questions_target=5
        )
        question = InterviewEngine.start_session(session)

        payload = {
            'question_id': question.id,
            'text': 'An array stores elements in contiguous memory locations with O(1) random access, whereas a linked list uses nodes with pointers with O(n) access.',
            'input_method': 'text',
            'duration_seconds': 25
        }
        response = self.client.post(
            reverse('api_submit_answer', args=[session.id]),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertIn('evaluation', json_data)
        self.assertIn('next_step', json_data)
        self.assertGreaterEqual(json_data['evaluation']['score'], 60.0)

    def test_end_interview_view(self):
        self.client.login(username='teststudent', password='Password123!')
        session = InterviewSession.objects.create(
            user=self.user,
            title='Ending Early',
            technical_domain='Python',
            total_questions_target=5
        )
        q = InterviewEngine.start_session(session)
        # Answer one question
        InterviewEngine.submit_answer(session, q.id, "Lists are mutable and tuples are immutable sequences.")

        response = self.client.post(reverse('interview_end', args=[session.id]))
        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.state, InterviewSession.STATE_COMPLETED)
        self.assertIsNotNone(session.overall_score)

    def test_history_and_deletion(self):
        self.client.login(username='teststudent', password='Password123!')
        session = InterviewSession.objects.create(
            user=self.user,
            title='History Session',
            technical_domain='DBMS and SQL',
            total_questions_target=5,
            state=InterviewSession.STATE_COMPLETED,
            overall_score=85.0
        )
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'History Session')

        # Delete session
        del_response = self.client.post(reverse('interview_delete', args=[session.id]))
        self.assertEqual(del_response.status_code, 302)
        self.assertFalse(InterviewSession.objects.filter(id=session.id).exists())

    def test_registration_and_login_flow(self):
        reg_data = {
            'username': 'newuser123',
            'email': 'newuser@college.edu',
            'password1': 'StrongPassword456!',
            'password2': 'StrongPassword456!'
        }
        reg_response = self.client.post(reverse('register'), data=reg_data)
        self.assertEqual(reg_response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser123').exists())
