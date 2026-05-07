from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from courses.models import Subject
from topics.models import Topic


class StudyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plans")
    subjects = models.ManyToManyField(Subject, related_name="study_plans")
    exam_date = models.DateField()
    hours_per_day = models.FloatField(validators=[MinValueValidator(0.5)])
    start_date = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Study Plan #{self.pk} for {self.user}"


class StudyTask(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE = "done"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_DONE, "Done"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name="tasks")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="study_tasks")
    date = models.DateField(db_index=True)
    duration = models.FloatField(validators=[MinValueValidator(0.05)])
    priority_score = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    sequence = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "sequence", "id"]
        indexes = [
            models.Index(fields=["plan", "date"]),
            models.Index(fields=["plan", "status"]),
        ]

    def __str__(self):
        return f"{self.topic.name} on {self.date} ({self.duration}h)"


class UserTopicKnowledge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topic_knowledge")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="user_knowledge")
    knowledge_level = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "topic")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} - {self.topic.name} ({self.knowledge_level}/5)"
