"""Context processors for Global Exchange Django project."""

from django.conf import settings


def stripe_context(request):
    """Add Stripe configuration to template context."""
    return {
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    }
