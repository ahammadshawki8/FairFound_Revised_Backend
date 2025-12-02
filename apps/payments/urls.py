from django.urls import path
from .views import CheckoutView, PaymentWebhookView, PaymentHistoryView

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('webhook/', PaymentWebhookView.as_view(), name='payment_webhook'),
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
]
