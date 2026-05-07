from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("courses", "__first__"),
        ("topics", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("exam_date", models.DateField()),
                ("hours_per_day", models.FloatField(validators=[django.core.validators.MinValueValidator(0.5)])),
                ("start_date", models.DateField(default=django.utils.timezone.localdate)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("subjects", models.ManyToManyField(related_name="study_plans", to="courses.subject")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="study_plans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UserTopicKnowledge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("knowledge_level", models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_knowledge", to="topics.topic")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="topic_knowledge", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"], "unique_together": {("user", "topic")}},
        ),
        migrations.CreateModel(
            name="StudyTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                ("duration", models.FloatField(validators=[django.core.validators.MinValueValidator(0.05)])),
                ("priority_score", models.FloatField(default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("done", "Done"), ("skipped", "Skipped")], default="pending", max_length=20)),
                ("sequence", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="planner.studyplan")),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="study_tasks", to="topics.topic")),
            ],
            options={"ordering": ["date", "sequence", "id"]},
        ),
        migrations.AddIndex(
            model_name="studytask",
            index=models.Index(fields=["plan", "date"], name="planner_stu_plan_id_98ec4f_idx"),
        ),
        migrations.AddIndex(
            model_name="studytask",
            index=models.Index(fields=["plan", "status"], name="planner_stu_plan_id_aecc13_idx"),
        ),
    ]
