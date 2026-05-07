from django.utils import timezone
from rest_framework import serializers

from courses.models import Subject
from topics.models import Topic

from .models import StudyPlan, StudyTask, UserTopicKnowledge


class PlannerTopicKnowledgeInputSerializer(serializers.Serializer):
    topic_id = serializers.IntegerField()
    knowledge_level = serializers.IntegerField(min_value=1, max_value=5)


class PlannerPlanCreateSerializer(serializers.Serializer):
    subject_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    exam_date = serializers.DateField()
    hours_per_day = serializers.FloatField(min_value=0.5)
    knowledge_levels = PlannerTopicKnowledgeInputSerializer(many=True, required=False)

    def validate_subject_ids(self, value):
        subjects = Subject.objects.filter(id__in=value).distinct()
        if subjects.count() != len(set(value)):
            raise serializers.ValidationError("One or more selected subjects do not exist.")
        return value

    def validate_exam_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Exam date cannot be in the past.")
        return value

    def validate_knowledge_levels(self, value):
        topic_ids = [item["topic_id"] for item in value]
        if len(topic_ids) != len(set(topic_ids)):
            raise serializers.ValidationError("Duplicate topic knowledge entries are not allowed.")
        return value

    def validate(self, attrs):
        topic_ids = [item["topic_id"] for item in attrs.get("knowledge_levels", [])]
        if not topic_ids:
            return attrs

        valid_topic_count = Topic.objects.filter(
            id__in=topic_ids,
            subject_id__in=attrs["subject_ids"],
        ).count()
        if valid_topic_count != len(set(topic_ids)):
            raise serializers.ValidationError(
                {"knowledge_levels": "Each topic knowledge entry must belong to one of the selected subjects."}
            )
        return attrs


class PlannerRescheduleSerializer(serializers.Serializer):
    exam_date = serializers.DateField(required=False)
    hours_per_day = serializers.FloatField(min_value=0.5, required=False)

    def validate_exam_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Exam date cannot be in the past.")
        return value


class StudyTaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StudyTask.STATUS_CHOICES)


class PlannerSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "slug"]


class PlannerTopicSerializer(serializers.ModelSerializer):
    subject = PlannerSubjectSerializer(read_only=True)
    knowledge_level = serializers.IntegerField(read_only=True)
    planner_priority = serializers.FloatField(read_only=True)
    adjusted_study_hours = serializers.FloatField(read_only=True)

    class Meta:
        model = Topic
        fields = [
            "id",
            "name",
            "subject",
            "pyq_frequency",
            "marks_weight",
            "estimated_time",
            "difficulty",
            "knowledge_level",
            "planner_priority",
            "adjusted_study_hours",
        ]


class StudyTaskSerializer(serializers.ModelSerializer):
    topic = PlannerTopicSerializer(read_only=True)
    subject = serializers.SerializerMethodField()

    class Meta:
        model = StudyTask
        fields = [
            "id",
            "topic",
            "subject",
            "date",
            "duration",
            "priority_score",
            "status",
            "sequence",
        ]

    def get_subject(self, obj):
        return {
            "id": obj.topic.subject_id,
            "name": obj.topic.subject.name,
            "slug": obj.topic.subject.slug,
        }


class StudyPlanSerializer(serializers.ModelSerializer):
    subjects = PlannerSubjectSerializer(many=True, read_only=True)
    tasks = StudyTaskSerializer(many=True, read_only=True)
    total_tasks = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()

    class Meta:
        model = StudyPlan
        fields = [
            "id",
            "subjects",
            "exam_date",
            "hours_per_day",
            "start_date",
            "is_active",
            "created_at",
            "updated_at",
            "total_tasks",
            "total_hours",
            "tasks",
        ]

    def get_total_tasks(self, obj):
        return obj.tasks.count()

    def get_total_hours(self, obj):
        return round(sum(float(task.duration) for task in obj.tasks.all()), 2)


class UserTopicKnowledgeSerializer(serializers.ModelSerializer):
    topic = PlannerTopicSerializer(read_only=True)

    class Meta:
        model = UserTopicKnowledge
        fields = ["id", "topic", "knowledge_level", "updated_at"]


class GenerateQuestionPaperSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    exam_type = serializers.ChoiceField(choices=["sessional", "semester"])
    difficulty = serializers.ChoiceField(choices=["easy", "balanced", "hard"], required=False)


class QuickAnswerSerializer(serializers.Serializer):
    question = serializers.CharField()
    subject_id = serializers.IntegerField(required=False)
    topic_id = serializers.IntegerField(required=False)
