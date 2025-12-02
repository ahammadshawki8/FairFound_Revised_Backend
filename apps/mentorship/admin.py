from django.contrib import admin
from .models import Session, MentorReview

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['mentor', 'mentee', 'date', 'time', 'status']

@admin.register(MentorReview)
class MentorReviewAdmin(admin.ModelAdmin):
    list_display = ['mentor', 'reviewer', 'rating', 'created_at']
