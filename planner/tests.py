from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from courses.models import Subject, Year
from planner.models import StudyTask
from planner.services import PlannerService
from topics.models import Topic


class PlannerServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="planner-user", password="pass1234")
        self.year = Year.objects.create(year=1, name="First Year", slug="1-year", status="published")
        self.subject = Subject.objects.create(name="Operating Systems", slug="operating-systems", status="published")
        self.subject.years.add(self.year)
        self.topic_one = Topic.objects.create(
            subject=self.subject,
            name="Deadlocks",
            pyq_frequency=4,
            marks_weight=8,
            estimated_time=2,
        )
        self.topic_two = Topic.objects.create(
            subject=self.subject,
            name="Scheduling",
            pyq_frequency=2,
            marks_weight=5,
            estimated_time=1.5,
        )

    def test_create_plan_generates_tasks(self):
        exam_date = timezone.localdate() + timedelta(days=4)
        plan = PlannerService.create_plan(
            user=self.user,
            subject_ids=[self.subject.id],
            exam_date=exam_date,
            hours_per_day=2,
            knowledge_overrides={self.topic_one.id: 2, self.topic_two.id: 4},
        )

        self.assertTrue(plan.is_active)
        self.assertEqual(plan.subjects.count(), 1)
        self.assertGreater(plan.tasks.count(), 0)
        self.assertTrue(all(task.duration > 0 for task in plan.tasks.all()))

    def test_reschedule_keeps_done_tasks_and_rebuilds_pending(self):
        exam_date = timezone.localdate() + timedelta(days=5)
        plan = PlannerService.create_plan(
            user=self.user,
            subject_ids=[self.subject.id],
            exam_date=exam_date,
            hours_per_day=1.5,
        )

        first_task = plan.tasks.order_by("date", "sequence").first()
        first_task.status = StudyTask.STATUS_DONE
        first_task.save(update_fields=["status", "updated_at"])

        pending_before = plan.tasks.filter(status=StudyTask.STATUS_PENDING).count()
        PlannerService.reschedule_plan(plan, hours_per_day=2)
        pending_after = plan.tasks.filter(status=StudyTask.STATUS_PENDING).count()

        self.assertEqual(plan.tasks.filter(status=StudyTask.STATUS_DONE).count(), 1)
        self.assertGreater(pending_before, 0)
        self.assertGreater(pending_after, 0)
