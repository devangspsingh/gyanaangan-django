from rest_framework import serializers
from courses.models import Course, Subject, Resource, Stream, Notification, SpecialPage, Year, EducationalYear
from accounts.models import Profile, SavedResource, Subscription
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import Truncator
from blog.models import BlogPost, Category
from taggit.serializers import (TagListSerializerField,
                              TaggitSerializer)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name')

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ('id', 'user', 'bio', 'emoji_tag', 'img_google_url')

class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ['id', 'year', 'slug', 'name', 'status']

class SimpleCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['name', 'slug']

class SimpleStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = ['name', 'slug']

class SimpleYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ['year', 'slug', 'name']

class EducationalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalYear
        fields = ['id', 'name']

class StreamForCourseSerializer(serializers.ModelSerializer):
    years = SimpleYearSerializer(many=True, read_only=True)
    og_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'description', 
            'meta_description', 'og_image_url', 'years', 'status',
            'common_name'
        ]
    
    def get_og_image_url(self, obj):
        if obj.og_image:
            return self.context['request'].build_absolute_uri(obj.og_image.url)
        return None

class CourseSerializer(serializers.ModelSerializer):
    streams = StreamForCourseSerializer(many=True, read_only=True)
    years = SimpleYearSerializer(many=True, read_only=True)
    og_image_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'description', 
            'meta_description', 'og_image_url', 'streams', 'years', 'status',
            'common_name'
        ]
    
    def get_og_image_url(self, obj):
        if obj.og_image:
            return self.context['request'].build_absolute_uri(obj.og_image.url)
        return None

    def get_description(self, obj):
        return obj.description or f"Explore the {obj.name} course, its streams, and available years."

    def get_meta_description(self, obj):
        return obj.meta_description or Truncator(obj.description or f"Detailed information about the {obj.name} course.").chars(160)

class StreamSerializer(serializers.ModelSerializer):
    years = SimpleYearSerializer(many=True, read_only=True)
    og_image_url = serializers.SerializerMethodField()
    courses = SimpleCourseSerializer(many=True, read_only=True)
    description = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'description', 
            'meta_description', 'og_image_url', 'years', 'status',
            'common_name', 'courses'
        ]

    def get_og_image_url(self, obj):
        if obj.og_image:
            return self.context['request'].build_absolute_uri(obj.og_image.url)
        return None

    def get_description(self, obj):
        return obj.description or f"Explore the {obj.name} stream and its available academic years."

    def get_meta_description(self, obj):
        return obj.meta_description or Truncator(obj.description or f"Detailed information about the {obj.name} stream.").chars(160)

class SubjectForSpecialPageSerializer(serializers.ModelSerializer):
    last_updated_info = serializers.SerializerMethodField()
    resource_count = serializers.IntegerField(source='resources.count', read_only=True)
    resource_types = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'slug', 'description', 'meta_description', 
            'og_image_url', 'last_updated_info', 'resource_types', 'url','resource_count'
        ]
    
    def get_og_image_url(self, obj):
        if obj.og_image:
            return self.context['request'].build_absolute_uri(obj.og_image.url)
        return None

    def get_last_updated_info(self, obj):
        updated_info = obj.get_last_updated_resource()
        if updated_info and updated_info.get('exact_time'):
            return {
                "status": updated_info["status"],
                "exact_time": updated_info["exact_time"].isoformat()
            }
        return updated_info

    def get_resource_types(self, obj):
        return list(obj.get_all_available_resource_types())

    def get_url(self, obj):
        return f"/subjects/{obj.slug}"

class SpecialPageSerializer(serializers.ModelSerializer):
    course = SimpleCourseSerializer(read_only=True)
    stream = SimpleStreamSerializer(read_only=True)
    year = SimpleYearSerializer(read_only=True)
    subjects = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta:
        model = SpecialPage
        fields = [
            'id', 'name', 'description', 'meta_description', 'og_image_url',
            'course', 'stream', 'year', 'subjects', 'status'
        ]

    def get_name(self, obj):
        return obj.name or f"{obj.course.name} - {obj.stream.name} ({obj.year.name})"

    def get_description(self, obj):
        return obj.description or f"Explore subjects and resources for {obj.course.name}, {obj.stream.name}, Year {obj.year.year}."

    def get_meta_description(self, obj):
        return obj.meta_description or Truncator(self.get_description(obj)).chars(160)

    def get_og_image_url(self, obj):
        if obj.og_image:
            return self.context['request'].build_absolute_uri(obj.og_image.url)
        return None
    
    def get_subjects(self, obj):
        if 'related_subjects' in self.context:
            subjects_qs = self.context['related_subjects']
        else:
            subjects_qs = Subject.published.filter(
                stream=obj.stream,
                years=obj.year,
            ).distinct()
        
        return SubjectForSpecialPageSerializer(subjects_qs, many=True, context=self.context).data

class ResourceSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    updated_at = serializers.CharField(source='get_last_updated_at.status', read_only=True)
    # view_url will now be the direct file URL
    view_url = serializers.SerializerMethodField() 
    download_url = serializers.SerializerMethodField()
    educational_year = EducationalYearSerializer(read_only=True)
    og_image_url = serializers.SerializerMethodField()


    class Meta:
        model = Resource
        fields = [
            'id', 'name', 'slug', 'resource_type', 'resource_type_display', 'file', 'privacy',
            'embed_link', 'subject', 'subject_name', 'educational_year', 'created_at', 'updated_at',
            'description', 'meta_description', 'og_image_url', 'is_saved', 'status',
            'view_url', 'download_url',
        ]
        read_only_fields = ['created_at', 'updated_at', 'resource_type_display', 'is_saved', 'view_url']

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedResource.objects.filter(
                user=request.user, 
                resource=obj
            ).exists()
        return False

    def get_og_image_url(self, obj):
        if obj.og_image:
            return self.context['request'].build_absolute_uri(obj.og_image.url)
        return None


    def get_view_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            # For S3Boto3Storage, obj.file.url generates a presigned URL if the bucket is private
            # and querystring_auth is True for the storage, or a direct URL if public.
            # Ensure your storage settings (PrivateMediaStorage/PublicMediaStorage) are correct.
            # If 'view' is in privacy, we provide the URL.
            if 'view' in obj.privacy:
                try:
                    # If it's a private file, this generates a presigned URL.
                    # If public, it's the direct URL.
                    return request.build_absolute_uri(obj.file.url)
                except Exception as e:
                    # Log error: print(f"Error generating file URL for {obj.name}: {e}")
                    return None
        elif obj.resource_type == Resource.VIDEO and obj.embed_link:
             # For videos, the embed_link can serve as the view_url if it's directly viewable
            return obj.embed_link
        return None

    def get_download_url(self, obj):
        request = self.context.get('request')
        # Download URL is only provided if user is authenticated AND resource allows download
        if request and request.user.is_authenticated and obj.file and 'download' in obj.privacy:
            # This uses the 'download' action URL from the ResourceViewSet
            return obj.file.url
        return None

class StreamNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = ('name', 'slug')

class SubjectSerializer(serializers.ModelSerializer):
    years = YearSerializer(many=True, read_only=True)
    resource_count = serializers.IntegerField(source='resources.count', read_only=True)
    last_updated_info = serializers.SerializerMethodField()
    resource_types = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'common_name', 'description',
            'meta_description', 'keywords', 'og_image_url', 'status',
            'stream', 
            'years',  
            'resource_count', 'last_updated_info', 'resource_types',
            'created_at', 'updated_at', 'last_resource_updated_at'
        ]

    def get_description(self, obj):
        return obj.description or f"Explore resources and materials for the subject: {obj.name}."

    def get_meta_description(self, obj):
        return obj.meta_description or Truncator(obj.description or f"Find notes, PYQs, and lab manuals for {obj.name}.").chars(160)

    def get_last_updated_info(self, obj):
        updated_info = obj.get_last_updated_resource()
        if updated_info and updated_info.get('exact_time'):
            return {
                "status": updated_info["status"],
                "exact_time": updated_info["exact_time"].isoformat()
            }
        return updated_info
    
    def get_resource_types(self, obj):
        return obj.get_all_available_resource_types()

    def get_og_image_url(self, obj):
        request = self.context.get('request')
        if obj.og_image and hasattr(obj.og_image, 'url'):
            return request.build_absolute_uri(obj.og_image.url)
        return None

class NotificationSerializer(serializers.ModelSerializer):
    content = serializers.CharField(source='message', read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'title', 'content', 'url', 'importance', 'tags', 'created_at')

class SubscriptionSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    stream = StreamSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = ('id', 'user', 'course', 'subject', 'stream', 'created_at')

class YearNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ('name', 'slug', 'year')

class SpecialPageSerializer(serializers.ModelSerializer):
    course = SimpleCourseSerializer(read_only=True)
    stream = SimpleStreamSerializer(read_only=True)
    year = SimpleYearSerializer(read_only=True)
    og_image_url = serializers.SerializerMethodField()
    notifications = NotificationSerializer(many=True, read_only=True)
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = SpecialPage
        fields = ('id', 'course', 'stream', 'year', 'description', 'og_image_url', 'notifications', 'subjects')
        lookup_field = 'id'

    def get_og_image_url(self, obj):
        request = self.context.get('request')
        if obj.og_image and hasattr(obj.og_image, 'url'):
            return request.build_absolute_uri(obj.og_image.url)
        return None

    def get_subjects(self, obj):
        related_subjects_qs = Subject.published.filter(
            stream=obj.stream,
            years=obj.year
        ).distinct()
        
        serializer = SubjectForSpecialPageSerializer(related_subjects_qs, many=True, context=self.context)
        return serializer.data

class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'post_count']

class BlogPostSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    category = CategorySerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'author_name', 'category', 
            'content', 'excerpt', 'featured_image', 'tags',
            'publish_date', 'is_featured', 'view_count', 
            'reading_time', 'meta_description', 'og_image'
        ]
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username
