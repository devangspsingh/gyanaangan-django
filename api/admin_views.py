from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
import pypdf
import io
import json

from courses.models import Course, Subject, Resource, Year, Stream, ContentManagementPermission, AIPromptTemplate, ContentManagementSettings, EducationalYear
from topics.services import LLMService
from django.contrib.auth import get_user_model
User = get_user_model()
from .serializers import (
    CourseSerializer,
    SubjectSerializer,
    ResourceSerializer,
    YearSerializer,
    StreamSerializer,
)

from rest_framework import serializers

class AdminSubjectSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()
    streams = serializers.SerializerMethodField()
    years = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'courses', 'streams', 'years']

    def get_courses(self, obj):
        # Subjects don't have courses directly, they have streams which belong to courses.
        # Alternatively, depending on the model, stream has a `courses` M2M field.
        courses = Course.objects.filter(streams__in=obj.stream.all()).distinct()
        return [c.id for c in courses]

    def get_streams(self, obj):
        return [s.id for s in obj.stream.all()]

    def get_years(self, obj):
        return [y.id for y in obj.years.all()]

class AIPromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPromptTemplate
        fields = ['id', 'name', 'naming_convention', 'description_prompt']

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class EducationalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalYear
        fields = ['id', 'name']

class IsContentManager(permissions.BasePermission):
    """
    Custom permission to only allow superusers or users with ContentManagementPermission to edit.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'content_management_permission')

class AdminResourceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = ResourceSerializer
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Resource.objects.all().order_by('-created_at')

        try:
            perm = user.content_management_permission
            courses = perm.courses.all()
            subjects = perm.subjects.all()

            # Subject → stream (M2M) → courses (M2M to Course)
            # ContentManagementPermission.years is Year (academic year), NOT EducationalYear,
            # so we don't filter by educational_year here to avoid model mismatch.
            queryset = Resource.objects.filter(
                Q(subject__in=subjects) |
                Q(subject__stream__courses__in=courses) |
                Q(uploaded_by=user)
            ).distinct().order_by('-created_at')
            return queryset
        except ContentManagementPermission.DoesNotExist:
            return Resource.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        uploaded_by_user = user
        
        if user.is_superuser:
            override_id = self.request.data.get('uploaded_by_id')
            if override_id:
                try:
                    uploaded_by_user = User.objects.get(id=override_id)
                except User.DoesNotExist:
                    pass
            else:
                try:
                    settings = ContentManagementSettings.load()
                    if settings.default_credit_user:
                        uploaded_by_user = settings.default_credit_user
                except Exception:
                    pass
        
        serializer.save(uploaded_by=uploaded_by_user)

class AdminCourseViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = CourseSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Course.objects.all()
        try:
            perm = user.content_management_permission
            if perm.courses.exists():
                return perm.courses.all()
            return Course.objects.all() # Or restrict to none if they don't have explicit course perm? Let's give all for dropdowns for now
        except ContentManagementPermission.DoesNotExist:
            return Course.objects.none()

class AdminYearViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = YearSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Year.objects.all()
        try:
            perm = user.content_management_permission
            if perm.years.exists():
                return perm.years.all()
            return Year.objects.all() # Fallback for dropdowns
        except ContentManagementPermission.DoesNotExist:
            return Year.objects.none()

class AdminStreamViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = StreamSerializer
    pagination_class = None

    def get_queryset(self):
        # We don't have explicit stream permissions yet, so return all streams
        # Or filter streams that belong to permitted courses
        user = self.request.user
        if user.is_superuser:
            return Stream.objects.all()
        try:
            perm = user.content_management_permission
            if perm.courses.exists():
                return Stream.objects.filter(courses__in=perm.courses.all()).distinct()
            return Stream.objects.all()
        except ContentManagementPermission.DoesNotExist:
            return Stream.objects.none()

class AdminSubjectViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = AdminSubjectSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Subject.objects.all()
        try:
            perm = user.content_management_permission
            if perm.subjects.exists():
                return perm.subjects.all()
            # If they have course permissions, show subjects of those courses
            if perm.courses.exists():
                # Subject → stream (M2M) → courses (M2M to Course)
                return Subject.objects.filter(stream__courses__in=perm.courses.all()).distinct()
            return Subject.objects.all() # Fallback for dropdown
        except ContentManagementPermission.DoesNotExist:
            return Subject.objects.none()

class AdminAIPromptTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = AIPromptTemplateSerializer
    queryset = AIPromptTemplate.objects.all()
    pagination_class = None

class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager] # Only content managers/superusers can search
    serializer_class = AdminUserSerializer
    
    def get_queryset(self):
        # We only want superusers to search for all users
        if not self.request.user.is_superuser:
            return User.objects.none()
            
        queryset = User.objects.all()
        query = self.request.query_params.get('search', None)
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
        return queryset[:20] # Limit to 20 for dropdown performance

class AdminEducationalYearViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsContentManager]
    serializer_class = EducationalYearSerializer
    queryset = EducationalYear.objects.all().order_by('-name')
    pagination_class = None

class AIGenerateContentView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, *args, **kwargs):
        filenames = request.data.get('filenames', [])
        subjects = request.data.get('subjects', [])
        educational_years = request.data.get('educational_years', [])
        naming_convention = request.data.get('naming_convention', '')
        custom_prompt = request.data.get('custom_prompt', '')
        
        if not filenames:
             return Response({"error": "No filenames provided."}, status=status.HTTP_400_BAD_REQUEST)

        system_prompt = (
            "You are an assistant that helps create metadata for educational resources. "
            "You will be given a list of file names, a list of available subjects (with IDs), and a list of available educational years (with IDs). "
            "For each file name, generate a suitable title (name), SEO-friendly description, meta description (max 160 chars), and keywords. "
            "Match the file name to the single most relevant subject from the provided list, and return its ID. If no subject matches, return null for subject_id.\n"
            "Determine the resource type (must be one of: 'notes', 'pyq', 'lab manual', 'video', 'pdf', 'image') and return it as 'resource_type'. If it's a previous year question paper, use 'pyq', if in title its sesisonal or semester pelase utilse PYQ only and not pdf.\n"
            "If the filename indicates an educational year, match it to the provided educational years list and return 'educational_year_id'. If no match, return null.\n"
            "Return the result ONLY as a valid JSON object containing a 'results' array. Each item in the array must have the keys: "
            "'original_filename', 'name', 'description', 'meta_description', 'keywords', 'subject_id', 'resource_type', 'educational_year_id'.\n"
        )
        
        if naming_convention:
            system_prompt += f"IMPORTANT: Use the following naming convention for the 'name' field: {naming_convention}\n"
            
        if custom_prompt:
            system_prompt += f"IMPORTANT INSTRUCTIONS: {custom_prompt}\n"
        
        user_prompt = f"File Names:\n" + "\n".join([f"- {f}" for f in filenames]) + "\n\n"
        user_prompt += f"Available Subjects:\n" + "\n".join([f"- ID: {s.get('id')}, Name: {s.get('name')}" for s in subjects]) + "\n\n"
        if educational_years:
            user_prompt += f"Available Educational Years:\n" + "\n".join([f"- ID: {y.get('id')}, Name: {y.get('name')}" for y in educational_years]) + "\n"

        try:
            # We use call_llm because we expect JSON
            response_json = LLMService.call_llm(system_prompt, user_prompt)
            if not response_json or 'results' not in response_json:
                 return Response({"error": "Failed to generate content from AI or invalid format."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(response_json, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
