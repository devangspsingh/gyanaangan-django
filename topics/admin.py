from django.contrib import admin
from django.contrib import messages
from .models import LLMProviderConfig, Topic, PYQTopicMap, SubjectAIProxy, ResourceAIProxy
from .services import LLMService

@admin.action(description="Extract Topics from Syllabus (AI)")
def extract_topics_from_syllabus(modeladmin, request, queryset):
    extracted_count = 0
    all_extracted_names = []
    for subject in queryset:
        try:
            topics = LLMService.process_syllabus(subject)
            extracted_count += len(topics)
            all_extracted_names.extend([t.name for t in topics])
        except Exception as e:
            modeladmin.message_user(request, f"Error processing {subject.name}: {str(e)}", level=messages.ERROR)
            return
            
    preview = ", ".join(all_extracted_names)
    if len(preview) > 200: preview = preview[:200] + "..."
            
    modeladmin.message_user(
        request, 
        f"Successfully extracted {extracted_count} topics. Preview: {preview}", 
        level=messages.SUCCESS
    )

@admin.action(description="Extract Topics from PYQs (AI)")
def extract_topics_from_pyqs(modeladmin, request, queryset):
    success_count = 0
    preview_mappings = []
    for resource in queryset.filter(resource_type="pyq"):
        # Use content field or original_file / PDF text extraction if available.
        # Assuming resource.content holds the text for now
        if resource.content:
            try:
                mappings = LLMService.extract_pyq_topics(resource, resource.content)
                if mappings:
                    success_count += len(mappings)
                    preview_mappings.extend([f"{m.topic.name} ({m.marks_type})" for m in mappings])
            except Exception as e:
                modeladmin.message_user(request, f"Error processing PYQ {resource.name}: {str(e)}", level=messages.ERROR)
                return
                
    preview = ", ".join(preview_mappings)
    if len(preview) > 200: preview = preview[:200] + "..."
    
    modeladmin.message_user(
        request, 
        f"Successfully processed {success_count} PYQ mapping(s). Preview: {preview}", 
        level=messages.SUCCESS
    )

@admin.register(SubjectAIProxy)
class SubjectAIProxyAdmin(admin.ModelAdmin):
    list_display = ('name', 'stream_names', 'has_syllabus')
    search_fields = ('name',)
    actions = [extract_topics_from_syllabus]
    
    def stream_names(self, obj):
        return ", ".join([s.name for s in obj.stream.all()])
        
    def has_syllabus(self, obj):
        return bool(obj.syllabus_text)
    has_syllabus.boolean = True

@admin.register(ResourceAIProxy)
class ResourceAIProxyAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'has_content')
    list_filter = ('subject', 'resource_type')
    search_fields = ('name', 'subject__name')
    actions = [extract_topics_from_pyqs]
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(resource_type="pyq")
        
    def has_content(self, obj):
        return bool(obj.content)
    has_content.boolean = True

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
