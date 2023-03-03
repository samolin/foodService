from django.conf import settings
from .models import Order


def get_stripe_key(request):
    return {'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY}
