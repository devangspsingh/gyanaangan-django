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
    BannerSerializer,  # Import BannerSerializer
    StudentProfileSerializer,  # Import StudentProfileSerializer
    SubscriptionSerializer,  # Import SubscriptionSerializer
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
from core.models import Banner
from accounts.models import Profile, SavedResource, Subscription, StudentProfile
from blog.models import BlogPost, Category
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.http import HttpResponse
from django.core.signing import TimestampSigner
from tracking.permissions import IsVisitorAllowed
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
    permission_classes = [IsVisitorAllowed]
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
    
    @action(detail=False, methods=['get'], url_path='me')
    def get_current_user_profile(self, request):
        """Get the current authenticated user's profile with permissions"""
        try:
            profile = Profile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


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
                        "is_staff": user.is_staff, # Include staff status for admin access
                        "is_superuser": user.is_superuser, # Include superuser status
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
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        # Annotate with count of only published posts
        return Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('-post_count', 'name')


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving active banners.
    Provides list of all active banners and detail view for individual banners.
    """
    queryset = Banner.active.all()
    serializer_class = BannerSerializer
    pagination_class = None  # No pagination for banners

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        """Return only currently active banners, ordered by display_order and primary status."""
        return Banner.active.all().order_by('display_order', '-is_primary', '-created_at')

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all currently active banners."""
        banners = self.get_queryset()
        serializer = self.get_serializer(banners, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def primary(self, request):
        """Get the primary banner if available."""
        primary_banner = self.get_queryset().filter(is_primary=True).first()
        if primary_banner:
            serializer = self.get_serializer(primary_banner)
            return Response(serializer.data)
        return Response({'detail': 'No primary banner found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def track_view(self, request, pk=None):
        """Track banner view (analytics)."""
        banner = self.get_object()
        banner.increment_view_count()
        return Response({'detail': 'View tracked successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def track_click(self, request, pk=None):
        """Track banner click (analytics)."""
        banner = self.get_object()
        banner.increment_click_count()
        return Response({'detail': 'Click tracked successfully.'}, status=status.HTTP_200_OK)

# Add these imports at the top
from rest_framework.permissions import IsAdminUser

# Add this new ViewSet after your existing BlogPostViewSet
class AdminBlogPostViewSet(viewsets.ModelViewSet):
    """
    Admin-only viewset for creating, updating, and deleting blog posts.
    Allows authenticated staff users to view and manage all posts including drafts.
    """
    queryset = BlogPost.objects.all()  # Using objects manager to get ALL posts
    serializer_class = BlogPostSerializer
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """
        Return all posts (including drafts) for authenticated staff users.
        Supports filtering by status via query parameter.
        """
        # Explicitly use objects.all() to get both published and draft posts
        queryset = BlogPost.objects.all().order_by('-created_at')
        
        # Filter by status if provided (e.g., ?status=draft or ?status=published)
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category if provided
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search) | 
                Q(excerpt__icontains=search)
            ).order_by('-created_at')
        
        return queryset

    def get_permissions(self):
        """
        Custom permissions - only staff/superusers can create/edit blogs
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'upload_image']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Automatically set the author to the current user"""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """Update blog post"""
        serializer.save()
    
    @action(detail=False, methods=['post'], url_path='upload-image')
    def upload_image(self, request):
        """
        Upload image for blog post content
        Accepts multipart/form-data with 'image' field
        Returns image URL for insertion into editor
        """
        if 'image' not in request.FILES:
            return Response(
                {"error": "No image provided. Please upload an image file."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response(
                {"error": f"Invalid file type. Allowed: {', '.join(allowed_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if image_file.size > max_size:
            return Response(
                {"error": "File too large. Maximum size is 5MB."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create a temporary BlogPost to use CKEditor's upload path
            # Or use a dedicated media upload model/path
            from django.core.files.storage import default_storage
            from django.utils.text import slugify
            import uuid
            
            # Generate unique filename
            ext = os.path.splitext(image_file.name)[1]
            filename = f"blog_images/{uuid.uuid4()}{ext}"
            
            # Save file (will use Minio if configured in settings)
            saved_path = default_storage.save(filename, image_file)
            image_url = default_storage.url(saved_path)
            
            # Return absolute URL
            if not image_url.startswith('http'):
                image_url = request.build_absolute_uri(image_url)
            
            logger.info(f"✅ Image uploaded successfully: {saved_path}")
            
            return Response({
                "url": image_url,
                "filename": image_file.name,
                "size": image_file.size
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"❌ Error uploading image: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to upload image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='upload-featured-image')
    def upload_featured_image(self, request, slug=None):
        """
        Upload featured image for a specific blog post
        """
        post = self.get_object()
        
        if 'image' not in request.FILES:
            return Response(
                {"error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validate file
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response(
                {"error": f"Invalid file type"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_size = 10 * 1024 * 1024  # 10MB for featured images
        if image_file.size > max_size:
            return Response(
                {"error": "File too large. Maximum 10MB"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Delete old featured image if exists
            if post.featured_image:
                post.featured_image.delete(save=False)
            
            # Save new featured image
            post.featured_image = image_file
            post.save()
            
            # Get absolute URL
            image_url = request.build_absolute_uri(post.featured_image.url)
            
            logger.info(f"✅ Featured image uploaded for post: {post.slug}")
            
            return Response({
                "url": image_url,
                "filename": image_file.name
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error uploading featured image: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='upload-og-image')
    def upload_og_image(self, request, slug=None):
        """
        Upload OG (Open Graph) image for a specific blog post
        """
        post = self.get_object()
        
        if 'image' not in request.FILES:
            return Response(
                {"error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validate file
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response(
                {"error": "Invalid file type"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_size = 5 * 1024 * 1024  # 5MB for OG images
        if image_file.size > max_size:
            return Response(
                {"error": "File too large. Maximum 5MB"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.core.files.storage import default_storage
            import uuid
            
            # Generate unique filename
            ext = os.path.splitext(image_file.name)[1]
            filename = f"og-image/{uuid.uuid4()}{ext}"
            
            # Delete old OG image if exists
            if post.og_image:
                post.og_image.delete(save=False)
            
            # Save file
            saved_path = default_storage.save(filename, image_file)
            
            # Update post
            post.og_image = saved_path
            post.save()
            
            # Get absolute URL
            image_url = default_storage.url(saved_path)
            if not image_url.startswith('http'):
                image_url = request.build_absolute_uri(image_url)
            
            logger.info(f"✅ OG image uploaded for post: {post.slug}")
            
            return Response({
                "url": image_url,
                "filename": image_file.name
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error uploading OG image: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryManagementViewSet(viewsets.ModelViewSet):
    """
    Admin viewset for managing blog categories
    """
    serializer_class = CategorySerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        # Annotate with count of all posts (including drafts) for admin view
        return Category.objects.annotate(
            post_count=Count('posts')
        ).order_by('-post_count', 'name')
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAuthenticated(), IsAdminUser()]


# Student Profile and Subscription ViewSets
class StudentProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student profiles
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own student profile
        return StudentProfile.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='me')
    def get_my_profile(self, request):
        """Get or create the current user's student profile"""
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post', 'put', 'patch'], url_path='update-me')
    def update_my_profile(self, request):
        """Update the current user's student profile"""
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subscriptions
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own subscriptions
        return Subscription.objects.filter(user=self.request.user).select_related(
            'course', 'subject', 'special_page', 
            'special_page__course', 'special_page__stream', 'special_page__year'
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='toggle-special-page')
    def toggle_special_page_subscription(self, request):
        """Toggle subscription to a special page (course/stream/year)"""
        special_page_id = request.data.get('special_page_id')
        
        if not special_page_id:
            return Response(
                {'error': 'special_page_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            special_page = SpecialPage.objects.get(id=special_page_id)
            print(special_page)
        except SpecialPage.DoesNotExist:
            return Response(
                {'error': 'Special page not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already subscribed
        is_subscribed = Subscription.is_subscribed(
            user=request.user,
            special_page=special_page
        )
        
        if is_subscribed:
            # Unsubscribe
            Subscription.unsubscribe(
                user=request.user,
                special_page=special_page
            )
            return Response({
                'subscribed': False,
                'message': 'Successfully unsubscribed'
            })
        else:
            # Subscribe
            subscription = Subscription.subscribe(
                user=request.user,
                special_page=special_page
            )
            serializer = self.get_serializer(subscription)
            return Response({
                'subscribed': True,
                'message': 'Successfully subscribed',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='toggle-subject')
    def toggle_subject_subscription(self, request):
        """Toggle subscription to a subject"""
        subject_id = request.data.get('subject_id')
        
        if not subject_id:
            return Response(
                {'error': 'subject_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response(
                {'error': 'Subject not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        is_subscribed = Subscription.is_subscribed(
            user=request.user,
            subject=subject
        )
        
        if is_subscribed:
            Subscription.unsubscribe(
                user=request.user,
                subject=subject
            )
            return Response({
                'subscribed': False,
                'message': 'Successfully unsubscribed'
            })
        else:
            subscription = Subscription.subscribe(
                user=request.user,
                subject=subject
            )
            serializer = self.get_serializer(subscription)
            return Response({
                'subscribed': True,
                'message': 'Successfully subscribed',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)