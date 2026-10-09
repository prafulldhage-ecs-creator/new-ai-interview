from interviews.services.ai_service import get_ai_service_status

def ai_status_processor(request):
    """Context processor providing AI provider status and application metadata to all templates."""
    return {
        'ai_status': get_ai_service_status(),
        'app_name': 'InterviewIQ',
        'app_tagline': 'AI Placement Interview Simulator'
    }
