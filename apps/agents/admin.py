from django.contrib import admin
from .models import IngestionJob, Evidence, ScoreSnapshot, BenchmarkCohort, SyntheticProfile


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'source', 'confidence', 'created_at']
    list_filter = ['source', 'confidence', 'created_at']
    search_fields = ['job__user__username']
    readonly_fields = ['created_at']


@admin.register(ScoreSnapshot)
class ScoreSnapshotAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'overall_score', 'confidence', 'flagged_for_human', 'reviewer', 'created_at']
    list_filter = ['flagged_for_human', 'confidence', 'created_at']
    search_fields = ['job__user__username']
    readonly_fields = ['created_at']


@admin.register(BenchmarkCohort)
class BenchmarkCohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'skill_category', 'sample_size', 'is_synthetic', 'updated_at']
    list_filter = ['skill_category', 'is_synthetic']
    search_fields = ['name', 'skill_category']
    readonly_fields = ['updated_at']


@admin.register(SyntheticProfile)
class SyntheticProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'category', 'overall_score', 'source', 'created_at']
    list_filter = ['category', 'source', 'created_at']
    search_fields = ['name', 'title']
    readonly_fields = ['created_at']
