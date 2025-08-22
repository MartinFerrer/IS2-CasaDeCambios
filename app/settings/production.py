'''This file extends base.py and contains settings specific to the production environment. Important considerations include:

    Debug mode turned off (DEBUG = False)
    Production database configurations (like PostgreSQL or MySQL)
    Security settings (e.g., ALLOWED_HOSTS, SECURE_BROWSER_XSS_FILTER, SECURE_CONTENT_TYPE_NOSNIFF)
    Configurations for static and media file handling (often using services like Amazon S3)
    Caching settings and any other performance-related configurations.
'''