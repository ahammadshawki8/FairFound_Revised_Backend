from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, FreelancerProfile, MentorProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'role', 'is_pro', 'level', 'xp']
    list_filter = ['role', 'is_pro', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('FairFound', {'fields': ('role', 'avatar', 'is_pro', 'xp', 'level', 'streak')}),
    )

@admin.register(FreelancerProfile)
class FreelancerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'hourly_rate', 'experience_years']

@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'rate', 'rating', 'is_available']
