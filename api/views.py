from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings
import requests
import os  # Add import for os.path.splitext
import logging  # Add logging
from django.core.files.base import ContentFile  # Add this import
from urllib.parse import urlparse  # Add this import to help with filename
from .serializers import (
    CourseSerializer,
    SubjectSerializer,
    ResourceSerializer,
    StreamSerializer,
    NotificationSerializer,
    ProfileSerializer,
    SpecialPageSerializer,  # Import SpecialPageSerializer
    BlogPostSerializer,  # Import BlogPostSerializer
    CategorySerializer,  # Import CategorySerializer
)
from courses.models import (
    Course,
    Subject,
    Resource,
    Stream,
    Notification,
    SpecialPage,
    Year  # Import Year model
)
from accounts.models import Profile, SavedResource
from blog.models import BlogPost, Category
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.http import HttpResponse
from django.core.signing import TimestampSigner
from urllib.parse import quote
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity, SearchVector
from django.db.models import Q, F, Count
from django.db.models.functions import Greatest
from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger(__name__)  # Initialize logger for this module


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 30


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.published.all().order_by('-updated_at', 'name')  # Ensure ordering
    serializer_class = CourseSerializer
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subject.published.all()  # Will use model's default ordering
    serializer_class = SubjectSerializer
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Subject.published.all()
        search_term = self.request.query_params.get("search", None)

        if search_term:
            # Assuming Subject model has a 'search_vector' field (SearchVectorField)
            # and fields like 'name', 'description', 'common_name', 'abbreviation'
            search_query = SearchQuery(search_term, config='english', search_type='websearch')
            
            # Annotate with similarity scores for ranking
            # Adjust weights as needed
            queryset = queryset.annotate(
                similarity=Greatest(
                    SearchRank(F('search_vector'), search_query, cover_density=True, normalization=2),
                    TrigramSimilarity('name', search_term) * 0.4,
                    TrigramSimilarity('description', search_term) * 0.2,
                    TrigramSimilarity('common_name', search_term) * 0.15,
                    TrigramSimilarity('abbreviation', search_term) * 0.1,
                    # Add other relevant text fields if any
                )
            ).filter(
                Q(search_vector=search_query) | Q(similarity__gt=0.05) # Adjust threshold as needed
            ).order_by('-similarity', '-last_resource_updated_at', 'name') # Primary sort by similarity
        else:
            queryset = queryset.order_by('-last_resource_updated_at', 'name') # Default ordering

        return queryset

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResourceSerializer
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination  # Ensure pagination is set

    def get_queryset(self):
        queryset = Resource.published.all()
        subject_slug = self.request.query_params.get("subject_slug", None)
        resource_type = self.request.query_params.get("resource_type", None)
        search_term = self.request.query_params.get("search", None)
        
        if subject_slug:
            queryset = queryset.filter(subject__slug=subject_slug)
        if resource_type and resource_type != 'all': # Handle 'all' if passed from client
            queryset = queryset.filter(resource_type=resource_type)

        if search_term:
            # Assuming Resource model has a 'search_vector' field
            # and fields like 'name', 'description', 'tags' (if tags are searchable text)
            search_query = SearchQuery(search_term, config='english', search_type='websearch')

            queryset = queryset.annotate(
                similarity=Greatest(
                    SearchRank(F('search_vector'), search_query, cover_density=True, normalization=2),
                    TrigramSimilarity('name', search_term) * 0.5,
                    TrigramSimilarity('description', search_term) * 0.3,
                    # If tags are stored as simple text or in a way TrigramSimilarity can be applied:
                    # TrigramSimilarity('tags_string_representation', search_term) * 0.2, 
                )
            ).filter(
                Q(search_vector=search_query) | Q(similarity__gt=0.05) # Adjust threshold
            ).order_by('-similarity', '-updated_at', 'name') # Primary sort by similarity
        else:
            queryset = queryset.order_by('-updated_at', 'name') # Default ordering

        return queryset

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def toggle_save(self, request, slug=None):
        resource = self.get_object()
        saved_resource, created = SavedResource.objects.get_or_create(
            user=request.user, resource=resource
        )
        if not created:
            saved_resource.delete()
        return Response({"saved": created})

    # Removed view_secure action as direct URL is now provided by serializer

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_name='download')
    def download(self, request, slug=None):
        logger.info(f"Attempting to download resource with slug: {slug}")
        try:
            resource = self.get_object()
            logger.info(f"Found resource for download: {resource.name} (ID: {resource.id}), File: {resource.file.name if resource.file else 'No File'}")
        except Exception as e:
            logger.error(f"Error in get_object for download with slug '{slug}': {e}", exc_info=True)
            return Response({"error": "Resource not found or not available for download."}, status=status.HTTP_404_NOT_FOUND)

        if not resource.file or not hasattr(resource.file, 'url'):
            logger.warning(f"File not found or no URL for resource: {resource.name} (ID: {resource.id}) during download")
            return Response({"error": "File not found for this resource."}, status=status.HTTP_404_NOT_FOUND)

        if 'download' not in resource.privacy and not request.user.is_staff:
            logger.warning(f"Permission denied for user {request.user} to download resource {resource.slug}")
            return Response({"error": "You do not have permission to download this resource."}, status=status.HTTP_403_FORBIDDEN)

        try:
            file_content = resource.file.read()
            content_type = 'application/octet-stream'

            response = HttpResponse(file_content, content_type=content_type)

            filename_base = resource.name  # Use resource name as base
            filename_ext = os.path.splitext(resource.file.name)[1] if resource.file.name and '.' in os.path.basename(resource.file.name) else '.dat'  # Default extension

            # Sanitize filename_base to prevent issues, e.g., remove characters not suitable for filenames
            # For simplicity, this example doesn't include extensive sanitization.
            safe_filename_base = "".join(c if c.isalnum() or c in (' ', '.', '-') else '_' for c in filename_base).rstrip()

            filename = quote(f"{safe_filename_base}{filename_ext}")
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            logger.info(f"Serving file {filename} for download.")
            return response
        except Exception as e:
            logger.error(f"Error serving file for download (slug: {slug}): {e}", exc_info=True)
            return Response({"error": "Could not serve the file for download."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StreamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stream.published.all()
    serializer_class = StreamSerializer
    lookup_field = "slug"

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.published.filter(show_until__gt=timezone.now()).order_by(
            "-created_at"
        )

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class UserProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class SavedResourceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResourceSerializer  # Uses ResourceSerializer, so context is needed

    def get_queryset(self):
        return Resource.published.filter(savedresource__user=self.request.user)

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class SpecialPageListViewSet(
    viewsets.ReadOnlyModelViewSet
):  # For listing special pages if needed
    queryset = SpecialPage.published.all()
    serializer_class = SpecialPageSerializer
    # Add filtering if necessary, e.g., by course

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}


class SpecialPageDetailView(APIView):
    permission_classes = [permissions.AllowAny]  # Or IsAuthenticated if needed

    def get_serializer_context(self):
        return {'request': self.request}

    def get(self, request, course_slug, stream_slug, year_slug, *args, **kwargs):
        try:
            course_obj = get_object_or_404(Course.published, slug=course_slug)
            stream_obj = get_object_or_404(Stream.published, slug=stream_slug)
            year_obj = get_object_or_404(Year.published, slug=year_slug)  # Assuming Year has a slug field
            
            special_page = get_object_or_404(
                SpecialPage.published,
                course=course_obj,
                stream=stream_obj,
                year=year_obj
            )

            # Fetch subjects related to this special page's course, stream, and year
            related_subjects = Subject.published.filter(
                # Assuming subjects are linked to streams and years.
                # Adjust filter based on your actual model relationships.
                # Example: If Subject has M2M to Stream and M2M to Year:
                stream=stream_obj,
                years=year_obj,
                # If subjects also need to be filtered by the course (e.g. stream belongs to multiple courses)
                # and Subject is related to Course (directly or indirectly):
                # Example: stream__courses=course_obj (if Stream has M2M to Course)
                # Example: courses=course_obj (if Subject has M2M to Course)
            ).distinct().order_by('-last_resource_updated_at', 'name') # Ensure consistent ordering
            
            context = self.get_serializer_context()
            context['related_subjects'] = related_subjects # Pass subjects to serializer context

            serializer = SpecialPageSerializer(special_page, context=context)
            return Response(serializer.data)
        except Course.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        except Stream.DoesNotExist:
            return Response({"error": "Stream not found."}, status=status.HTTP_404_NOT_FOUND)
        except Year.DoesNotExist:
            return Response({"error": "Year not found."}, status=status.HTTP_404_NOT_FOUND)
        except SpecialPage.DoesNotExist:
            return Response({"error": "Special page not found for the given criteria."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching special page details: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny] # Allow unauthenticated access

    def post(self, request):
        id_token = request.data.get("id_token") # Changed from access_token to id_token

        if not id_token:
            return Response(
                {"error": "ID token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Verify token with Google's tokeninfo endpoint
            token_info_url = "https://oauth2.googleapis.com/tokeninfo"
            token_info_response = requests.get(
                token_info_url, params={"id_token": id_token}
            )

            if not token_info_response.ok:
                logger.error(f"Failed to verify Google ID token: {token_info_response.status_code} - {token_info_response.text}")
                return Response(
                    {"error": "Failed to verify Google ID token", "details": token_info_response.json()},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_info = token_info_response.json()

            # Verify audience (aud claim)
            if user_info.get("aud") != settings.GOOGLE_CLIENT_ID:
                logger.error(f"ID token audience mismatch. Expected: {settings.GOOGLE_CLIENT_ID}, Got: {user_info.get('aud')}")
                return Response(
                    {"error": "Invalid token: Audience mismatch."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Verify issuer (iss claim)
            if user_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
                logger.error(f"Invalid token: Issuer mismatch. Got: {user_info.get('iss')}")
                return Response(
                    {"error": "Invalid token: Issuer mismatch."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email = user_info.get("email")
            name = user_info.get("name")
            picture_url = user_info.get("picture") # URL of the Google profile picture

            if not email:
                return Response(
                    {"error": "Email not provided in token"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Get or create user
            User = get_user_model()
            # Ensure username is unique, email is a good candidate if it's verified
            user, created = User.objects.get_or_create(
                email=email, # Use email as the primary lookup
                defaults={"username": email, "first_name": name} # Set username to email by default
            )
            if not created: # If user exists, update name if it changed
                if user.first_name != name:
                    user.first_name = name
                if user.username != email: # If username was different from email, update it
                    # This case needs careful handling if usernames must be unique and email changes
                    # For simplicity, we assume email is stable or username is derived from email
                    user.username = email 
                user.save()


            # Update profile
            profile, profile_created = Profile.objects.get_or_create(user=user)
            
            if profile_created:
                profile.bio = f"This is {name}'s bio."
                profile.emoji_tag = "😊"
            
            # Update img_google_url and attempt to download/update profile_pic
            if picture_url and profile.img_google_url != picture_url:
                profile.img_google_url = picture_url
                try:
                    img_response = requests.get(picture_url, stream=True)
                    if img_response.status_code == 200:
                        # Try to get a reasonable filename
                        parsed_url = urlparse(picture_url)
                        img_name_base, img_ext = os.path.splitext(os.path.basename(parsed_url.path))
                        
                        # Google URLs might not have extensions, or might be complex.
                        # Use content type if available, otherwise default.
                        content_type = img_response.headers.get('content-type')
                        if not img_ext and content_type:
                            if 'jpeg' in content_type or 'jpg' in content_type:
                                img_ext = '.jpg'
                            elif 'png' in content_type:
                                img_ext = '.png'
                            elif 'gif' in content_type:
                                img_ext = '.gif'
                            else: # Fallback for unknown image types from content-type
                                img_ext = '.jpg' 
                        elif not img_ext: # If no extension and no content type, default
                            img_ext = '.jpg'

                        # Sanitize base name or use a generic one
                        img_filename = f"{user.username}_google_pic{img_ext}"
                        
                        profile.profile_pic.save(img_filename, ContentFile(img_response.content), save=False)
                        logger.info(f"Successfully downloaded and saved Google profile picture for {user.email} as {img_filename}")
                    else:
                        logger.warning(f"Failed to download Google profile picture for {user.email}. Status: {img_response.status_code}")
                except Exception as e:
                    logger.error(f"Error downloading or saving Google profile picture for {user.email}: {e}", exc_info=True)
            
            profile.save()


            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            profile_pic_url_to_return = None
            if profile.profile_pic and hasattr(profile.profile_pic, 'url'):
                profile_pic_url_to_return = profile.profile_pic.url

            # The user data returned here is sourced from your 'user' and 'profile' objects,
            # which reflect the state in your database after processing Google's information.
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username, 
                        "name": user.first_name, # Sourced from the User model
                        "picture": profile_pic_url_to_return, # Use the URL of the saved ImageField
                    },
                }
            )

        except Exception as e:
            logger.error(f"Google login error: {e}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred during Google login.", "details": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GlobalSearchAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination  # Note: APIView doesn't use this directly like ViewSets

    def get_serializer_context(self):  # Add context for serializers
        return {'request': self.request}

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "")
        if not query:
            return Response(
                {"courses": [], "subjects": [], "resources": []},
                status=status.HTTP_200_OK,
            )

        search_query_obj = SearchQuery(query, config="english", search_type="websearch")

        # Courses
        courses_qs = (
            Course.published.annotate(
                similarity=Greatest(
                    SearchRank(
                        F("search_vector"),
                        search_query_obj,
                        cover_density=True,
                        normalization=2,
                    ),
                    TrigramSimilarity("name", query) * 0.4,
                    TrigramSimilarity("description", query) * 0.2,
                    TrigramSimilarity("meta_description", query) * 0.1,
                )
            )
            .filter(Q(search_vector=search_query_obj) | Q(similarity__gt=0.05))
            .order_by("-similarity")
        )

        # Subjects
        subjects_qs_initial = (
            Subject.published.annotate(
                similarity=Greatest(
                    SearchRank(
                        F("search_vector"),
                        search_query_obj,
                        cover_density=True,
                        normalization=2,
                    ),
                    TrigramSimilarity("name", query) * 0.4,
                    TrigramSimilarity("description", query) * 0.2,
                    TrigramSimilarity("meta_description", query) * 0.1,
                )
            )
            .filter(Q(search_vector=search_query_obj) | Q(similarity__gt=0.05))
            .order_by("-similarity")
        )

        top_subjects_instances = list(
            subjects_qs_initial[:10]
        )  # Get top 10 subject instances
        top_subject_ids = [s.id for s in top_subjects_instances]

        # Fetch related resources for these top subjects
        # We use a subquery or a separate query to get resources for these subjects
        # and then attach them. For simplicity and given the limit, direct filtering is okay.

        subjects_data_with_resources = []
        for subj_instance in top_subjects_instances:
            # Fetch top 3 resources for this subject, ordered by relevance or date
            # This is a simplified approach. For better performance on many subjects,
            # consider prefetching or a more optimized bulk query.
            related_resources_qs = (
                Resource.published.filter(subject=subj_instance)
                .annotate(
                    resource_similarity=(
                        Greatest(  # Optional: rank resources if they also match query
                            SearchRank(
                                F("search_vector"),
                                search_query_obj,
                                cover_density=True,
                                normalization=2,
                            ),
                            TrigramSimilarity("name", query) * 0.3,
                            TrigramSimilarity("description", query) * 0.1,
                        )
                        if query
                        else F("updated_at")
                    )  # Fallback to date if no query for ranking
                )
                .order_by("-resource_similarity" if query else "-updated_at")[:3]
            )

            subj_data = SubjectSerializer(
                subj_instance, context=self.get_serializer_context()  # Pass context
            ).data
            subj_data["related_resources"] = ResourceSerializer(
                related_resources_qs, many=True, context=self.get_serializer_context()  # Pass context
            ).data
            subjects_data_with_resources.append(subj_data)

        # General Resources (not necessarily tied to the top subjects, or could be filtered out if already shown)
        resources_qs = (
            Resource.published.annotate(
                similarity=Greatest(
                    SearchRank(
                        F("search_vector"),
                        search_query_obj,
                        cover_density=True,
                        normalization=2,
                    ),
                    TrigramSimilarity("name", query) * 0.4,
                    TrigramSimilarity("description", query) * 0.2,
                    TrigramSimilarity("meta_description", query) * 0.1,
                )
            )
            .filter(Q(search_vector=search_query_obj) | Q(similarity__gt=0.05))
            .order_by("-similarity")
        )

        course_serializer = CourseSerializer(
            courses_qs[:10], many=True, context=self.get_serializer_context()  # Pass context
        )
        # Use the subjects_data_with_resources which now includes related_resources
        # subject_serializer = SubjectSerializer(subjects_qs[:10], many=True, context=self.get_serializer_context())
        resource_serializer = ResourceSerializer(
            resources_qs[:10], many=True, context=self.get_serializer_context()  # Pass context
        )

        return Response(
            {
                "courses": course_serializer.data,
                "subjects": subjects_data_with_resources,  # Use augmented data
                "resources": resource_serializer.data,
            }
        )

class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BlogPost.published.all()
    serializer_class = BlogPostSerializer
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = BlogPost.published.all()
        category = self.request.query_params.get('category', None)
        tag = self.request.query_params.get('tag', None)
        search = self.request.query_params.get('search', None)

        if category:
            queryset = queryset.filter(category__slug=category)
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if search:
            search_query = SearchQuery(search, config='english', search_type='websearch')
            queryset = queryset.annotate(
                similarity=Greatest(
                    SearchRank(F('search_vector'), search_query),
                    TrigramSimilarity('title', search) * 0.4,
                    TrigramSimilarity('content', search) * 0.2,
                    TrigramSimilarity('excerpt', search) * 0.3
                )
            ).filter(
                Q(search_vector=search_query) | Q(similarity__gt=0.1)
            ).order_by('-similarity', '-publish_date')
        
        return queryset

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_posts = self.get_queryset().filter(is_featured=True)[:5]
        serializer = self.get_serializer(featured_posts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        popular_posts = self.get_queryset().order_by('-view_count')[:5]
        serializer = self.get_serializer(popular_posts, many=True)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.annotate(post_count=Count('posts'))
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return self.queryset.filter(posts__status='published').distinct()
