from django.contrib import admin
from .models import Challenge, ChallengeParticipant, Badge, ChallengeProgress

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_type', 'start_date', 'end_date', 'is_active', 'current_participants_count']
    list_filter = ['target_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    readonly_fields = ['current_participants_count', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'

@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'status', 'current_streak', 'max_streak', 'joined_at']
    list_filter = ['status', 'challenge', 'joined_at']
    search_fields = ['user__username', 'challenge__name']
    readonly_fields = ['joined_at', 'updated_at']
    date_hierarchy = 'joined_at'

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'challenge', 'is_acquired', 'acquired_date']
    list_filter = ['is_acquired', 'challenge', 'acquired_date']
    search_fields = ['name', 'user__username', 'challenge__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'acquired_date'

@admin.register(ChallengeProgress)
class ChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ['participant', 'date', 'target_achieved', 'actual_value']
    list_filter = ['target_achieved', 'date', 'participant__challenge']
    search_fields = ['participant__user__username', 'participant__challenge__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
