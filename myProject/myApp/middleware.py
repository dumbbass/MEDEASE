from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware

class AdminSessionMiddleware(SessionMiddleware):
    def process_request(self, request):
        if request.path.startswith('/admin/'):
            request.session_cookie_name = settings.ADMIN_SESSION_COOKIE_NAME
        else:
            request.session_cookie_name = settings.SESSION_COOKIE_NAME
        return super().process_request(request) 