from django.contrib import admin
from .models import Portfolio, PortfolioProject, Proposal

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'tagline', 'updated_at']

@admin.register(PortfolioProject)
class PortfolioProjectAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'title', 'order']

@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ['user', 'client_name', 'tone', 'created_at']
