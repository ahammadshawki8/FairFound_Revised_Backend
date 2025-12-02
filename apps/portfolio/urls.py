from django.urls import path
from .views import PortfolioView, GeneratePortfolioView

urlpatterns = [
    path('', PortfolioView.as_view(), name='portfolio'),
    path('generate/', GeneratePortfolioView.as_view(), name='portfolio_generate'),
]
