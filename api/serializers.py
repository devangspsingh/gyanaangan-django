from rest_framework import serializers
from courses.models import Course, Subject, Resource, Stream, Notification, SpecialPage, Year, EducationalYear
from accounts.models import Profile, SavedResource, Subscription, StudentProfile
from core.models import SEODetail, Banner
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import Truncator
from blog.models import BlogPost, Category
from taggit.serializers import (TagListSerializerField,
                              TaggitSerializer)

class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'is_staff', 'is_superuser')

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    profile_pic_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Profile
        fields = ('id', 'user', 'bio', 'emoji_tag', 'img_google_url', 'profile_pic_url')
    
    def get_profile_pic_url(self, obj):
        if obj.profile_pic and hasattr(obj.profile_pic, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_pic.url)
            return obj.profile_pic.url
        return None
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
        fields = ['id', 'year', 'slug', 'name']

class EducationalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalYear
        fields = ['id', 'name']

class StudentProfileSerializer(serializers.ModelSerializer):
    course = SimpleCourseSerializer(read_only=True)
    stream = SimpleStreamSerializer(read_only=True)
    year = SimpleYearSerializer(read_only=True)
    
    course_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    stream_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    year_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'course', 'stream', 'year', 'college_name', 
            'mobile_number', 'year_of_graduation', 'is_profile_complete',
            'course_id', 'stream_id', 'year_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['is_profile_complete', 'created_at', 'updated_at']
        
        extra_kwargs = {
            'college_name': {
                'required': False, 

            },
            'mobile_number': {
                'required': False, 

            },
           
        }
        
    def create(self, validated_data):
        course_id = validated_data.pop('course_id', None)
        stream_id = validated_data.pop('stream_id', None)
        year_id = validated_data.pop('year_id', None)
        
        if course_id:
            validated_data['course_id'] = course_id
        if stream_id:
            validated_data['stream_id'] = stream_id
        if year_id:
            validated_data['year_id'] = year_id
            
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        course_id = validated_data.pop('course_id', None)
        stream_id = validated_data.pop('stream_id', None)
        year_id = validated_data.pop('year_id', None)
        
        if course_id is not None:
            validated_data['course_id'] = course_id
        if stream_id is not None:
            validated_data['stream_id'] = stream_id
        if year_id is not None:
            validated_data['year_id'] = year_id
            
        return super().update(instance, validated_data)


class SubscriptionSerializer(serializers.ModelSerializer):
    course = SimpleCourseSerializer(read_only=True)
    subject = serializers.SerializerMethodField()
    special_page = serializers.SerializerMethodField()
    
    course_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    subject_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    special_page_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'course', 'subject', 'special_page',
            'course_id', 'subject_id', 'special_page_id',
            'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_subject(self, obj):
        if obj.subject:
            return {
                'id': obj.subject.id,
                'name': obj.subject.name,
                'slug': obj.subject.slug
            }
        return None
    
    def get_special_page(self, obj):
        if obj.special_page:
            return {
                'id': obj.special_page.id,
                'course': obj.special_page.course.name,
                'stream': obj.special_page.stream.name,
                'year': obj.special_page.year.name,
                'course_slug': obj.special_page.course.slug,
                'stream_slug': obj.special_page.stream.slug,
                'year_slug': obj.special_page.year.slug,
            }
        return None


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
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'slug', 'description', 'meta_description', 
            'og_image_url', 'last_updated_info', 'resource_types', 'url','resource_count', 'is_subscribed'
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
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.is_subscribed(
                user=request.user,
                subject=obj
            )
        return False

class SpecialPageSerializer(serializers.ModelSerializer):
    course = SimpleCourseSerializer(read_only=True)
    stream = SimpleStreamSerializer(read_only=True)
    year = SimpleYearSerializer(read_only=True)
    subjects = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = SpecialPage
        fields = [
            'id', 'name', 'description', 'meta_description', 'og_image_url',
            'course', 'stream', 'year', 'subjects', 'status', 'is_subscribed'
        ]

    def get_name(self, obj):
        return obj.name or f"{obj.course.name} - {obj.stream.name} ({obj.year.name})"

    def get_description(self, obj):
        return obj.description or f"Explore subjects and resources for {obj.course.name}, {obj.stream.name}, Year {obj.year.year}."

    def get_meta_description(self, obj):
        return obj.meta_description or Truncator(self.get_description(obj)).chars(160)
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.is_subscribed(
                user=request.user,
                special_page=obj
            )
        return False

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
    subject_slug = serializers.CharField(source='subject.slug', read_only=True, allow_null=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    updated_at = serializers.CharField(source='get_last_updated_at.status', read_only=True)
    # view_url will now be the direct file URL or resource link
    view_url = serializers.SerializerMethodField() 
    download_url = serializers.SerializerMethodField()
    educational_year = EducationalYearSerializer(read_only=True)
    og_image_url = serializers.SerializerMethodField()


    class Meta:
        model = Resource
        fields = [
            'id', 'name', 'slug', 'resource_type', 'resource_type_display', 'file', 'privacy',
            'embed_link', 'resource_link', 'content', 'subject','subject_slug', 'subject_name', 'educational_year', 'created_at', 'updated_at',
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
        
        # Priority 1: If file exists and view is allowed (uploaded PDFs, images, etc.)
        if obj.file and hasattr(obj.file, 'url') and 'view' in obj.privacy:
            try:
                # If it's a private file, this generates a presigned URL.
                # If public, it's the direct URL.
                return request.build_absolute_uri(obj.file.url)
            except Exception as e:
                # Log error: print(f"Error generating file URL for {obj.name}: {e}")
                return None
        
        # Priority 2: For videos, use embed_link (YouTube embeds)
        if obj.resource_type == Resource.VIDEO and obj.embed_link:
             # For videos, the embed_link can serve as the view_url if it's directly viewable
            return obj.embed_link
        
        # Priority 3: If resource_link exists (external PDF/document link)
        if obj.resource_link:
            return obj.resource_link
        
        # Priority 4: Content is rendered on frontend, no URL needed
        # (Frontend will check for resource.content field)
        
        return None

    def get_download_url(self, obj):
        request = self.context.get('request')
        
        # If resource_link exists and download is allowed, return it
        if obj.resource_link and 'download' in obj.privacy:
            return obj.resource_link
        
        # Download URL is only provided if user is authenticated AND resource allows download
        if request and request.user.is_authenticated and obj.file and 'download' in obj.privacy:
            # This uses the 'download' action URL from the ResourceViewSet
            return obj.file.url
        
        return None


class ResourceSimpleSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='subject.name', read_only=True, allow_null=True)
    subject_slug = serializers.CharField(source='subject.slug', read_only=True, allow_null=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    updated_at = serializers.CharField(source='get_last_updated_at.status', read_only=True)
    # view_url will now be the direct file URL or resource link
    # view_url = serializers.SerializerMethodField() 
    # download_url = serializers.SerializerMethodField()
    educational_year = EducationalYearSerializer(read_only=True)
    # og_image_url = serializers.SerializerMethodField()


    class Meta:
        model = Resource
        fields = [
            'id', 'name', 'slug', 'resource_type', 'resource_type_display',
             'subject','subject_slug', 'subject_name', 'educational_year', 'created_at', 'updated_at',
            'description', 'meta_description', 'is_saved'

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

    # def get_og_image_url(self, obj):
    #     if obj.og_image:
    #         return self.context['request'].build_absolute_uri(obj.og_image.url)
    #     return None


    # def get_view_url(self, obj):
    #     request = self.context.get('request')
        
    #     # Priority 1: If file exists and view is allowed (uploaded PDFs, images, etc.)
    #     if obj.file and hasattr(obj.file, 'url') and 'view' in obj.privacy:
    #         try:
    #             # If it's a private file, this generates a presigned URL.
    #             # If public, it's the direct URL.
    #             return request.build_absolute_uri(obj.file.url)
    #         except Exception as e:
    #             # Log error: print(f"Error generating file URL for {obj.name}: {e}")
    #             return None
        
    #     # Priority 2: For videos, use embed_link (YouTube embeds)
    #     if obj.resource_type == Resource.VIDEO and obj.embed_link:
    #          # For videos, the embed_link can serve as the view_url if it's directly viewable
    #         return obj.embed_link
        
    #     # Priority 3: If resource_link exists (external PDF/document link)
    #     if obj.resource_link:
    #         return obj.resource_link
        
    #     # Priority 4: Content is rendered on frontend, no URL needed
    #     # (Frontend will check for resource.content field)
        
    #     return None

    # def get_download_url(self, obj):
    #     request = self.context.get('request')
        
    #     # If resource_link exists and download is allowed, return it
    #     if obj.resource_link and 'download' in obj.privacy:
    #         return obj.resource_link
        
    #     # Download URL is only provided if user is authenticated AND resource allows download
    #     if request and request.user.is_authenticated and obj.file and 'download' in obj.privacy:
    #         # This uses the 'download' action URL from the ResourceViewSet
    #         return obj.file.url
        
    #     return None

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
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'slug', 'abbreviation', 'common_name', 'description',
            'meta_description', 'keywords', 'og_image_url', 'status',
            'stream', 
            'years',  
            'resource_count', 'last_updated_info', 'resource_types',
            'created_at', 'updated_at', 'last_resource_updated_at', 'is_subscribed'
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
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.is_subscribed(
                user=request.user,
                subject=obj
            )
        return False

class NotificationSerializer(serializers.ModelSerializer):
    content = serializers.CharField(source='message', read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'title', 'content', 'url', 'importance', 'tags', 'created_at')

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
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = SpecialPage
        fields = ('id', 'course', 'stream', 'year', 'description', 'og_image_url', 'notifications', 'subjects', 'is_subscribed')
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
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.is_subscribed(
                user=request.user,
                special_page=obj
            )
        return False

class SubscriptionSerializer(serializers.ModelSerializer):
    course = SimpleCourseSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    stream = SimpleStreamSerializer(read_only=True)
    special_page = SpecialPageSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = ('id', 'user', 'course', 'subject', 'stream','special_page', 'created_at')

class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'post_count']

class BlogPostSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    author_name = serializers.SerializerMethodField()
    # author_username = serializers.SerializerMethodField()
    author_profile_picture = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    featured_image_url = serializers.SerializerMethodField()
    # Make image fields optional for write operations
    featured_image = serializers.ImageField(required=False, allow_null=True)
    og_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'author', 'author_name', 'tags',
            'author_profile_picture', 'category', 'category_id',
            'content', 'excerpt', 'featured_image', 'featured_image_url',
            'publish_date', 'is_featured', 'sticky_post', 
            'reading_time', 'meta_description', 'keywords', 'og_image', 'og_image_url',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'slug', 'reading_time', 'created_at', 'updated_at']
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username
    
    # def get_author_username(self, obj):
    #     return obj.author.username
    
    def get_author_profile_picture(self, obj):
        try:
            profile = obj.author.profile
            if profile.profile_pic:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.profile_pic.url)
                return profile.profile_pic.url
        except Exception:
            pass
        return None
    
    def get_og_image_url(self, obj):
        if obj.og_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.og_image.url)
            return obj.og_image.url
        return None
    
    def get_featured_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None
    
    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category_id'] = category_id
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id is not None:
            validated_data['category_id'] = category_id
        return super().update(instance, validated_data)


class BlogPostSimpleSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    author_name = serializers.SerializerMethodField()
    # author_username = serializers.SerializerMethodField()
    author_profile_picture = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    featured_image_url = serializers.SerializerMethodField()
    # Make image fields optional for write operations
    featured_image = serializers.ImageField(required=False, allow_null=True)
    og_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'author', 'author_name', 'tags',
            'category', 'category_id',
            'featured_image', 'featured_image_url',
            'publish_date', 'is_featured', 'sticky_post', 
            'reading_time', 'og_image', 'og_image_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'slug', 'reading_time', 'created_at', 'updated_at']
    
    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username
    
    # def get_author_username(self, obj):
    #     return obj.author.username
    
    def get_author_profile_picture(self, obj):
        try:
            profile = obj.author.profile
            if profile.profile_pic:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.profile_pic.url)
                return profile.profile_pic.url
        except Exception:
            pass
        return None
    
    def get_og_image_url(self, obj):
        if obj.og_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.og_image.url)
            return obj.og_image.url
        return None
    
    def get_featured_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None
    
    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category_id'] = category_id
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id is not None:
            validated_data['category_id'] = category_id
        return super().update(instance, validated_data)


class BannerSerializer(serializers.ModelSerializer):
    """
    Serializer for Banner model with computed fields for frontend display.
    """
    image_url = serializers.SerializerMethodField()
    mobile_image_url = serializers.SerializerMethodField()
    is_currently_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Banner
        fields = [
            'id',
            'title',
            'description',
            'image',
            'image_url',
            'mobile_image',
            'mobile_image_url',
            'link_url',
            'link_text',
            'is_primary',
            'is_active',
            'active_from',
            'active_until',
            'display_order',
            'view_count',
            'is_currently_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['view_count', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        """Get absolute URL for banner image."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_mobile_image_url(self, obj):
        """Get absolute URL for mobile banner image, fallback to desktop image."""
        image = obj.mobile_image if obj.mobile_image else obj.image
        if image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(image.url)
            return image.url
        return None
    
    def get_is_currently_active(self, obj):
        """Check if banner is currently active based on time range."""
        return obj.is_currently_active()
