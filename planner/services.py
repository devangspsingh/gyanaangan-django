from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import StudentProfile
from courses.models import Subject
from topics.models import Topic

from .models import StudyPlan, StudyTask, UserTopicKnowledge


@dataclass
class PlannerTopicSnapshot:
    topic: Topic
    knowledge_level: int
    priority_score: float
    study_hours: float


class PlannerService:
    MIN_COMPRESSED_STUDY_HOURS = 0.05

    @staticmethod
    def resolve_subjects_for_user(user, explicit_subject_ids=None):
        if explicit_subject_ids:
            subjects = Subject.objects.filter(id__in=explicit_subject_ids).distinct()
        else:
            profile = StudentProfile.objects.filter(user=user).select_related("stream", "year").first()
            if not profile or not profile.year:
                return Subject.objects.none()

            subjects = Subject.objects.filter(years=profile.year)
            if profile.stream:
                subjects = subjects.filter(stream=profile.stream)
            subjects = subjects.distinct()

        return subjects

    @staticmethod
    def get_topic_knowledge_map(user, topics, knowledge_overrides=None):
        topic_ids = [topic.id for topic in topics]
        stored_knowledge = {
            item.topic_id: item.knowledge_level
            for item in UserTopicKnowledge.objects.filter(user=user, topic_id__in=topic_ids)
        }
        overrides = knowledge_overrides or {}
        resolved = {}
        for topic in topics:
            knowledge_level = overrides.get(topic.id, stored_knowledge.get(topic.id, 3))
            resolved[topic.id] = Topic.normalize_knowledge_level(knowledge_level)
        return resolved

    @staticmethod
    def build_topic_snapshots(user, subjects, knowledge_overrides=None):
        topics = list(
            Topic.objects.filter(subject__in=subjects)
            .select_related("subject")
            .order_by("-pyq_frequency", "-marks_weight", "name")
        )
        if not topics:
            return []

        knowledge_map = PlannerService.get_topic_knowledge_map(user, topics, knowledge_overrides)
        snapshots = []
        for topic in topics:
            knowledge_level = knowledge_map[topic.id]
            snapshots.append(
                PlannerTopicSnapshot(
                    topic=topic,
                    knowledge_level=knowledge_level,
                    priority_score=topic.get_planner_priority(knowledge_level),
                    study_hours=max(topic.get_adjusted_study_hours(knowledge_level), 0.25),
                )
            )

        snapshots.sort(key=lambda item: (-item.priority_score, -item.study_hours, item.topic.name.lower()))
        return snapshots

    @staticmethod
    def persist_knowledge_levels(user, knowledge_overrides):
        if not knowledge_overrides:
            return

        for topic_id, knowledge_level in knowledge_overrides.items():
            UserTopicKnowledge.objects.update_or_create(
                user=user,
                topic_id=topic_id,
                defaults={"knowledge_level": Topic.normalize_knowledge_level(knowledge_level)},
            )

    @staticmethod
    def _allocate_tasks(plan, entries, start_date):
        total_days = max((plan.exam_date - start_date).days + 1, 1)
        total_capacity = total_days * float(plan.hours_per_day)
        total_requested = sum(float(entry["remaining_hours"]) for entry in entries)

        if total_requested > total_capacity and total_requested > 0:
            min_hours = PlannerService.MIN_COMPRESSED_STUDY_HOURS
            if entries and len(entries) * min_hours > total_capacity:
                min_hours = max(total_capacity / len(entries), 0.01)

            variable_budget = max(total_capacity - (len(entries) * min_hours), 0)
            variable_requested = sum(max(float(entry["remaining_hours"]) - min_hours, 0) for entry in entries)

            for entry in entries:
                base_hours = min_hours
                extra_requested = max(float(entry["remaining_hours"]) - min_hours, 0)
                extra_hours = (extra_requested / variable_requested) * variable_budget if variable_requested > 0 else 0
                entry["remaining_hours"] = round(base_hours + extra_hours, 2)

        current_date = start_date
        remaining_capacity = float(plan.hours_per_day)
        sequence = 1
        created_tasks = []

        while entries and current_date <= plan.exam_date:
            if remaining_capacity <= 0:
                current_date = current_date + timedelta(days=1)
                remaining_capacity = float(plan.hours_per_day)
                continue

            current_entry = entries[0]
            block_duration = min(current_entry["remaining_hours"], remaining_capacity)

            created_tasks.append(
                StudyTask(
                    plan=plan,
                    topic=current_entry["topic"],
                    date=current_date,
                    duration=round(block_duration, 2),
                    priority_score=round(current_entry["priority_score"], 2),
                    status=StudyTask.STATUS_PENDING,
                    sequence=sequence,
                )
            )
            sequence += 1

            current_entry["remaining_hours"] = round(current_entry["remaining_hours"] - block_duration, 2)
            remaining_capacity = round(remaining_capacity - block_duration, 2)

            if current_entry["remaining_hours"] <= 0:
                entries.pop(0)

            if remaining_capacity <= 0:
                current_date = current_date + timedelta(days=1)
                remaining_capacity = float(plan.hours_per_day)

        StudyTask.objects.bulk_create(created_tasks)
        return created_tasks

    @staticmethod
    @transaction.atomic
    def create_plan(user, subject_ids, exam_date, hours_per_day, knowledge_overrides=None):
        today = timezone.localdate()
        if exam_date < today:
            raise ValidationError("Exam date cannot be in the past.")

        subjects = PlannerService.resolve_subjects_for_user(user, subject_ids)
        if not subjects.exists():
            raise ValidationError("No matching subjects found for the planner.")

        snapshots = PlannerService.build_topic_snapshots(user, subjects, knowledge_overrides)
        if not snapshots:
            raise ValidationError("No extracted topics found for the selected subjects.")

        PlannerService.persist_knowledge_levels(user, knowledge_overrides or {})
        StudyPlan.objects.filter(user=user, is_active=True).update(is_active=False)

        plan = StudyPlan.objects.create(
            user=user,
            exam_date=exam_date,
            hours_per_day=hours_per_day,
            start_date=today,
            is_active=True,
        )
        plan.subjects.set(subjects)

        entries = [
            {
                "topic": snapshot.topic,
                "priority_score": snapshot.priority_score,
                "remaining_hours": snapshot.study_hours,
            }
            for snapshot in snapshots
        ]
        PlannerService._allocate_tasks(plan, entries, start_date=today)
        return plan

    @staticmethod
    @transaction.atomic
    def reschedule_plan(plan, exam_date=None, hours_per_day=None):
        today = timezone.localdate()

        if exam_date is not None:
            if exam_date < today:
                raise ValidationError("Exam date cannot be in the past.")
            plan.exam_date = exam_date

        if hours_per_day is not None:
            plan.hours_per_day = hours_per_day

        pending_hours = (
            plan.tasks.filter(status__in=[StudyTask.STATUS_PENDING, StudyTask.STATUS_SKIPPED], date__gte=today)
            .values("topic_id")
            .annotate(total_hours=Sum("duration"))
        )

        if not pending_hours:
            plan.save(update_fields=["exam_date", "hours_per_day", "updated_at"])
            return plan

        topics = {
            topic.id: topic
            for topic in Topic.objects.filter(id__in=[item["topic_id"] for item in pending_hours]).select_related("subject")
        }
        knowledge_map = PlannerService.get_topic_knowledge_map(plan.user, list(topics.values()))

        entries = []
        for item in pending_hours:
            topic = topics.get(item["topic_id"])
            if not topic:
                continue
            knowledge_level = knowledge_map.get(topic.id, 3)
            entries.append(
                {
                    "topic": topic,
                    "priority_score": topic.get_planner_priority(knowledge_level),
                    "remaining_hours": float(item["total_hours"] or 0),
                }
            )

        entries.sort(key=lambda item: (-item["priority_score"], -item["remaining_hours"], item["topic"].name.lower()))

        plan.tasks.filter(status__in=[StudyTask.STATUS_PENDING, StudyTask.STATUS_SKIPPED], date__gte=today).delete()
        plan.save(update_fields=["exam_date", "hours_per_day", "updated_at"])
        PlannerService._allocate_tasks(plan, entries, start_date=today)
        return plan

    @staticmethod
    def get_current_plan(user):
        return (
            StudyPlan.objects.filter(user=user, is_active=True)
            .prefetch_related("subjects", "tasks__topic__subject")
            .first()
        )

    @staticmethod
    def get_dashboard_data(user):
        today = timezone.localdate()
        current_plan = PlannerService.get_current_plan(user)
        if not current_plan:
            return {
                "current_plan": None,
                "today_tasks": [],
                "upcoming_tasks": [],
                "stats": {
                    "completed_this_week": 0,
                    "pending_today": 0,
                    "study_hours_today": 0,
                    "days_until_exam": None,
                },
            }

        today_tasks = list(
            current_plan.tasks.filter(date=today).select_related("topic", "topic__subject").order_by("sequence", "id")
        )
        upcoming_tasks = list(
            current_plan.tasks.filter(date__gt=today).select_related("topic", "topic__subject").order_by("date", "sequence", "id")[:5]
        )
        week_start = today - timedelta(days=today.weekday())

        completed_this_week = current_plan.tasks.filter(
            status=StudyTask.STATUS_DONE,
            updated_at__date__gte=week_start,
            updated_at__date__lte=today,
        ).count()
        study_hours_today = sum(float(task.duration) for task in today_tasks)

        return {
            "current_plan": current_plan,
            "today_tasks": today_tasks,
            "upcoming_tasks": upcoming_tasks,
            "stats": {
                "completed_this_week": completed_this_week,
                "pending_today": sum(1 for task in today_tasks if task.status == StudyTask.STATUS_PENDING),
                "study_hours_today": round(study_hours_today, 2),
                "days_until_exam": (current_plan.exam_date - today).days,
            },
        }
