"""
Django middleware for auto-instrumentation.

This is a stub implementation for future Django support.
The pattern will be similar to FastAPI middleware but adapted to Django's
middleware conventions.

Usage (future):
    # settings.py
    MIDDLEWARE = [
        'inev_sdk.integrations.django.INEVMiddleware',
        # ... other middleware
    ]

    INEV = {
        'api_key': 'sk_live_...',
        'project_id': 'proj_123',
        'excluded_paths': ['/health', '/admin'],
    }
"""


class INEVMiddleware:
    """
    Django middleware for auto-instrumentation (stub).

    TODO: Implement Django middleware following Django conventions:
    - Use __init__(get_response) pattern
    - Support both sync and async views
    - Extract user from request.user
    - Handle Django's session framework
    """

    def __init__(self, get_response):
        self.get_response = get_response
        raise NotImplementedError(
            "Django middleware is not yet implemented. "
            "Use FastAPI middleware or explicit SDK instrumentation for now. "
            "See: https://docs.inev.io/sdk/django"
        )

    def __call__(self, request):
        response = self.get_response(request)
        return response
