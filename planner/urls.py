from django.urls import path

from .views import (
    PlannerCurrentPlanView,
    PlannerDashboardView,
    PlannerGeneratePlanView,
    PlannerRescheduleView,
    PlannerTaskListView,
    PlannerTaskStatusUpdateView,
    PlannerTopicListView,
)

urlpatterns = [
    path("topics/", PlannerTopicListView.as_view(), name="planner-topics"),
    path("plans/current/", PlannerCurrentPlanView.as_view(), name="planner-current-plan"),
    path("plans/generate/", PlannerGeneratePlanView.as_view(), name="planner-generate-plan"),
    path("plans/current/reschedule/", PlannerRescheduleView.as_view(), name="planner-reschedule-plan"),
    path("tasks/", PlannerTaskListView.as_view(), name="planner-task-list"),
    path("tasks/<int:task_id>/status/", PlannerTaskStatusUpdateView.as_view(), name="planner-task-status"),
    path("dashboard/", PlannerDashboardView.as_view(), name="planner-dashboard"),
]
