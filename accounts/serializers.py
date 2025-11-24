from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile, StudentProfile

User = get_user_model()

class MinimalUserSerializer(serializers.ModelSerializer):
    """
    Minimal user serializer for embedding in other resources.
    Exposes only non-sensitive public information.
    """
    full_name = serializers.SerializerMethodField()
    profile_pic_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'profile_pic_url']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "User"

    def get_profile_pic_url(self, obj):
        try:
            if hasattr(obj, 'profile') and obj.profile.profile_pic:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.profile.profile_pic.url)
                return obj.profile.profile_pic.url
        except Exception:
            pass
        return None


class PublicUserSerializer(serializers.ModelSerializer):
    """
    Full public user profile serializer.
    Excludes PII like email and username.
    Includes profile and student profile information if available.
    """
    full_name = serializers.SerializerMethodField()
    profile_pic_url = serializers.SerializerMethodField()
    bio = serializers.CharField(source='profile.bio', read_only=True)
    emoji_tag = serializers.CharField(source='profile.emoji_tag', read_only=True)
    
    # Student Profile Fields
    college_name = serializers.CharField(source='student_profile.college_name', read_only=True)
    course_name = serializers.CharField(source='student_profile.course.name', read_only=True)
    stream_name = serializers.CharField(source='student_profile.stream.name', read_only=True)
    year_name = serializers.CharField(source='student_profile.year.name', read_only=True)
    year_of_graduation = serializers.IntegerField(source='student_profile.year_of_graduation', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'profile_pic_url', 'bio', 'emoji_tag',
            'college_name', 'course_name', 'stream_name', 'year_name', 'year_of_graduation'
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "User"

    def get_profile_pic_url(self, obj):
        try:
            if hasattr(obj, 'profile') and obj.profile.profile_pic:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.profile.profile_pic.url)
                return obj.profile.profile_pic.url
        except Exception:
            pass
        return None
