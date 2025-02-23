MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Add these settings
SESSION_COOKIE_NAME = 'regular_user_sessionid'
ADMIN_SESSION_COOKIE_NAME = 'admin_sessionid'

MIDDLEWARE = [
    # ... other middleware ...
    'myApp.middleware.AdminSessionMiddleware',
    # ... rest of middleware ...
]

# Configure session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours in seconds 

# Doctor registration settings
DOCTOR_REGISTRATION_CODES = [
    'DOCTOR123',
    'ADMIN456',
    # Add more codes as needed
] 