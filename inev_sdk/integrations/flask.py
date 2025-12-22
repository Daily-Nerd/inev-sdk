"""
Flask middleware for auto-instrumentation.

This is a stub implementation for future Flask support.
The pattern will be similar to FastAPI middleware but adapted to Flask's
before_request/after_request hooks.

Usage (future):
    from flask import Flask
    from inev_sdk.integrations.flask import INEVMiddleware

    app = Flask(__name__)
    INEVMiddleware(
        app,
        api_key='sk_live_...',
        project_id='proj_123',
        excluded_paths=['/health', '/metrics'],
    )
"""


class INEVMiddleware:
    """
    Flask middleware for auto-instrumentation (stub).

    TODO: Implement Flask middleware using before_request/after_request:
    - Use @app.before_request to capture request start
    - Use @app.after_request to capture response
    - Use @app.teardown_request for cleanup
    - Extract user from flask.g.user or session
    """

    def __init__(
        self,
        app,
        api_key: str,
        project_id: str,
        endpoint: str = "https://api.inev.io",
        excluded_paths: list[str] | None = None,
    ):
        self.app = app
        self.api_key = api_key
        self.project_id = project_id
        raise NotImplementedError(
            "Flask middleware is not yet implemented. "
            "Use FastAPI middleware or explicit SDK instrumentation for now. "
            "See: https://docs.inev.io/sdk/flask"
        )
