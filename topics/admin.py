from django.contrib import admin
from django.contrib import messages
from .models import LLMProviderConfig, Topic, PYQTopicMap
from .services import LLMService

@admin.register(LLMProviderConfig)
class LLMProviderConfigAdmin(admin.ModelAdmin):
    list_display = ('provider', 'model_name', 'is_active')
    list_filter = ('is_active', 'provider')
    search_fields = ('model_name', 'provider')

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'pyq_frequency', 'marks_weight', 'priority', 'difficulty', 'created_at')
    list_filter = ('subject', 'difficulty')
    search_fields = ('name', 'subject__name')
    readonly_fields = ('created_at',)

@admin.register(PYQTopicMap)
class PYQTopicMapAdmin(admin.ModelAdmin):
    list_display = ('topic', 'marks_type', 'weight', 'resource')
    list_filter = ('marks_type', 'topic__subject')
    search_fields = ('question_text', 'topic__name')
