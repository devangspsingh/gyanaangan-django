from django.db import models
from courses.models import Subject, Resource

class LLMProviderConfig(models.Model):
    PROVIDER_CHOICES = [
        ('groq', 'Groq'),
        ('openrouter', 'OpenRouter'),
    ]
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    api_key = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100, default='llama-3.1-70b-versatile', help_text="e.g. meta-llama/Llama-3-70b-chat-hf for OpenRouter")
    is_active = models.BooleanField(default=False, help_text="Only one provider can be active at a time.")
    
    def save(self, *args, **kwargs):
        if self.is_active:
            # Ensure only one provider is active at a time
            LLMProviderConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_provider_display()} ({self.model_name}) - {'Active' if self.is_active else 'Inactive'}"

    class Meta:
        verbose_name = "LLM Provider Config"
        verbose_name_plural = "LLM Provider Configs"


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=255)
    
    # Derived data
    pyq_frequency = models.IntegerField(default=0)
    marks_weight = models.IntegerField(default=0)
    
    # AI enrichment
    difficulty = models.IntegerField(default=1)
    
    # Optional
    estimated_time = models.FloatField(default=1.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def priority(self):
        # Priority Logic computed synchronously (no LLM needed here)
        return (self.pyq_frequency * 0.7) + (self.marks_weight * 0.3)
        
    def __str__(self):
        return f"{self.name} - {self.subject.name}"


class PYQTopicMap(models.Model):
    MARKS_TYPE_CHOICES = [
        ("short", "Short"),
        ("long", "Long")
    ]
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="question_mappings")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    marks_type = models.CharField(max_length=10, choices=MARKS_TYPE_CHOICES)
    weight = models.IntegerField(default=5)
    
    def __str__(self):
        return f"{self.topic.name} - {self.get_marks_type_display()} (Wt: {self.weight})"

class SubjectAIProxy(Subject):
    class Meta:
        proxy = True
        verbose_name = "Subject AI Extraction"
        verbose_name_plural = "Subject AI Extractions"

class ResourceAIProxy(Resource):
    class Meta:
        proxy = True
        verbose_name = "PYQ AI Extraction"
        verbose_name_plural = "PYQ AI Extractions"
