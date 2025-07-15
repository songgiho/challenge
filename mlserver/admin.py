from django.contrib import admin
from .models import MassEstimationTask, FoodItem


@admin.register(MassEstimationTask)
class MassEstimationTaskAdmin(admin.ModelAdmin):
    list_display = ['task_id', 'status', 'progress', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['task_id']
    readonly_fields = ['task_id', 'created_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('task_id', 'status', 'progress', 'message', 'error')
        }),
        ('이미지', {
            'fields': ('image',)
        }),
        ('결과', {
            'fields': ('result_data',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ['food_name', 'estimated_mass_g', 'confidence', 'task', 'created_at']
    list_filter = ['verification_method', 'created_at']
    search_fields = ['food_name', 'task__task_id']
    readonly_fields = ['created_at']
