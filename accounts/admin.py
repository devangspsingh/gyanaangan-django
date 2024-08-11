from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile  # Correctly specify the model here
    can_delete = False
    verbose_name_plural = "Profile"


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "view_profile_link",
    )

    def view_profile_link(self, obj):
        url = reverse("admin:accounts_profile_change", args=[obj.profile.id])
        return format_html('<a href="{}">View Profile</a>', url)

    view_profile_link.short_description = "Profile"


class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bio", "emoji_tag", "img_google_url")
    search_fields = ("user__username", "bio")


admin.site.register(Profile, ProfileAdmin)
# Unregister the default User admin
admin.site.unregister(User)
# Register the custom User admin
admin.site.register(User, UserAdmin)
