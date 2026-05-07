from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Subject
from topics.models import Topic
from topics.services import LLMService

from .models import StudyTask
from .serializers import (
    GenerateQuestionPaperSerializer,
    PlannerPlanCreateSerializer,
    PlannerRescheduleSerializer,
    PlannerTopicSerializer,
    QuickAnswerSerializer,
    StudyPlanSerializer,
    StudyTaskSerializer,
    StudyTaskStatusSerializer,
)
from .services import PlannerService


def _parse_subject_ids(request):
    raw_values = request.query_params.getlist("subject_ids")
    if not raw_values:
        raw_csv = request.query_params.get("subject_ids")
        raw_values = raw_csv.split(",") if raw_csv else []
    return [int(subject_id) for subject_id in raw_values if str(subject_id).strip().isdigit()]


def _serialize_planner_topics(user, subjects):
    snapshots = PlannerService.build_topic_snapshots(user, subjects)
    payload = []
    for snapshot in snapshots:
        payload.append(
            {
                "id": snapshot.topic.id,
                "name": snapshot.topic.name,
                "subject": snapshot.topic.subject,
                "pyq_frequency": snapshot.topic.pyq_frequency,
                "marks_weight": snapshot.topic.marks_weight,
                "estimated_time": snapshot.topic.estimated_time,
                "difficulty": snapshot.topic.difficulty,
                "knowledge_level": snapshot.knowledge_level,
                "planner_priority": round(snapshot.priority_score, 2),
                "adjusted_study_hours": round(snapshot.study_hours, 2),
            }
        )
    return PlannerTopicSerializer(payload, many=True).data


class PlannerTopicListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subject_ids = _parse_subject_ids(request)
        subjects = PlannerService.resolve_subjects_for_user(request.user, subject_ids or None)

        if not subjects.exists():
            return Response({"results": [], "count": 0})

        data = _serialize_planner_topics(request.user, subjects)
        return Response({"results": data, "count": len(data)})


class PlannerGeneratePlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PlannerPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        knowledge_overrides = {
            item["topic_id"]: item["knowledge_level"]
            for item in serializer.validated_data.get("knowledge_levels", [])
        }

        try:
            plan = PlannerService.create_plan(
                user=request.user,
                subject_ids=serializer.validated_data["subject_ids"],
                exam_date=serializer.validated_data["exam_date"],
                hours_per_day=serializer.validated_data["hours_per_day"],
                knowledge_overrides=knowledge_overrides,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StudyPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class PlannerCurrentPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        plan = PlannerService.get_current_plan(request.user)
        if not plan:
            return Response({"detail": "No active study plan found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StudyPlanSerializer(plan).data)


class PlannerRescheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan = PlannerService.get_current_plan(request.user)
        if not plan:
            return Response({"detail": "No active study plan found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PlannerRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            plan = PlannerService.reschedule_plan(
                plan,
                exam_date=serializer.validated_data.get("exam_date"),
                hours_per_day=serializer.validated_data.get("hours_per_day"),
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StudyPlanSerializer(plan).data)


class PlannerTaskStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, task_id):
        try:
            task = StudyTask.objects.select_related("plan").get(id=task_id, plan__user=request.user)
        except StudyTask.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudyTaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task.status = serializer.validated_data["status"]
        task.save(update_fields=["status", "updated_at"])
        return Response(StudyTaskSerializer(task).data)


class PlannerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        dashboard = PlannerService.get_dashboard_data(request.user)
        current_plan = dashboard["current_plan"]

        return Response(
            {
                "current_plan": StudyPlanSerializer(current_plan).data if current_plan else None,
                "today_tasks": StudyTaskSerializer(dashboard["today_tasks"], many=True).data,
                "upcoming_tasks": StudyTaskSerializer(dashboard["upcoming_tasks"], many=True).data,
                "stats": dashboard["stats"],
            }
        )


class PlannerTaskListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        plan = PlannerService.get_current_plan(request.user)
        if not plan:
            return Response({"results": [], "count": 0})

        today = timezone.localdate()
        scope = request.query_params.get("scope", "today")
        queryset = plan.tasks.select_related("topic", "topic__subject").order_by("date", "sequence", "id")

        if scope == "today":
            queryset = queryset.filter(date=today)
        elif scope == "upcoming":
            queryset = queryset.filter(date__gt=today)
        elif scope == "pending":
            queryset = queryset.filter(status=StudyTask.STATUS_PENDING)

        serialized = StudyTaskSerializer(queryset, many=True).data
        return Response({"results": serialized, "count": len(serialized)})


class GenerateQuestionPaperView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GenerateQuestionPaperSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            subject = Subject.objects.get(id=serializer.validated_data["subject_id"])
        except Subject.DoesNotExist:
            return Response({"detail": "Subject not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            paper = LLMService.generate_question_paper(
                subject=subject,
                exam_type=serializer.validated_data["exam_type"],
                difficulty=serializer.validated_data.get("difficulty"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"paper": paper})


class QuickAnswerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = QuickAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subject = None
        topic = None

        subject_id = serializer.validated_data.get("subject_id")
        topic_id = serializer.validated_data.get("topic_id")

        if subject_id is not None:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                return Response({"detail": "Subject not found."}, status=status.HTTP_404_NOT_FOUND)

        if topic_id is not None:
            try:
                topic = Topic.objects.select_related("subject").get(id=topic_id)
            except Topic.DoesNotExist:
                return Response({"detail": "Topic not found."}, status=status.HTTP_404_NOT_FOUND)
            if subject is None:
                subject = topic.subject

        try:
            answer = LLMService.generate_quick_answer(
                question=serializer.validated_data["question"],
                subject=subject,
                topic=topic,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"answer": answer})
