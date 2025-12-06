from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import Profile, SavedResource, Subscription, StudentProfile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    readonly_fields = ("profile_picture",)

    def profile_picture(self, obj):
        if obj.profile_pic:
            return format_html(
                '<img src="{}" width="150" height="150" style="border-radius: 50%;" />',
                obj.profile_pic.url,
            )
        return "No Image"

    profile_picture.short_description = "Profile Picture"


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "profile_picture",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "date_joined",
        "view_profile_link",
    )
    ordering = ("-date_joined",)  # Order users by most recently joined

    def profile_picture(self, obj):
        if hasattr(obj, "profile") and obj.profile.profile_pic:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius: 50%;" />',
                obj.profile.profile_pic.url,
            )
        return "No Image"

    profile_picture.short_description = "DP"

    def view_profile_link(self, obj):
        url = reverse("admin:accounts_profile_change", args=[obj.profile.id])
        return format_html('<a href="{}">View Profile</a>', url)

    view_profile_link.short_description = "Profile"


class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "profile_picture",
        "bio",
        "emoji_tag",
        "img_google_url",
    )
    readonly_fields = ("profile_picture",)
    search_fields = ("user__username", "bio")
    ordering = ("user__username",)  # Order profiles by most recently updated

    def profile_picture(self, obj):
        if obj.profile_pic:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.profile_pic.url,
            )
        return "No Image"

    profile_picture.short_description = "Picture"


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "get_subscription_type",
        "get_subscription_name",
        "created_at",
    )
    list_filter = ("user", "created_at")
    search_fields = (
        "user__username",
        "course__name",
        # "stream__name",
        "subject__name",
        "special_page",
    )

    def get_subscription_type(self, obj):
        if obj.course:
            return "Course"
        # elif obj.stream:
        #     return "Stream"
        elif obj.subject:
            return "Subject"
        elif obj.special_page:
            return "Special Page"
        return "Unknown"

    get_subscription_type.short_description = "Subscription Type"

    def get_subscription_name(self, obj):
        if obj.course:
            return obj.course.name
       
        elif obj.subject:
            return obj.subject.name
        elif obj.special_page:
            return obj.special_page
        return "N/A"

    get_subscription_name.short_description = "Subscription Name"


class SavedResourceAdmin(admin.ModelAdmin):
    list_display = ("user", "resource", "saved_at")
    list_filter = ("user", "resource", "saved_at")
    search_fields = ("user__username", "resource__name")
    ordering = ("-saved_at",)  # Order by most recent saved resource


class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "course",
        "stream",
        "year",
        "college_name",
        "is_profile_complete",
        "created_at",
    )
    list_filter = ("is_profile_complete", "course", "stream", "year", "created_at")
    search_fields = ("user__username", "college_name", "mobile_number")
    ordering = ("-created_at",)
    readonly_fields = ("is_profile_complete", "created_at", "updated_at")


# Unregister the default User admin
admin.site.unregister(User)
# Register the custom User admin
admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(SavedResource, SavedResourceAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
