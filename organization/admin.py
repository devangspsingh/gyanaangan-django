from django.contrib import admin
from .models import Organization, OrganizationMember, OrganizationGallery


class OrganizationMemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 0
    fields = ['user', 'role', 'is_active', 'joined_at']
    readonly_fields = ['joined_at']
    can_delete = True


class OrganizationGalleryInline(admin.TabularInline):
    model = OrganizationGallery
    extra = 0
    fields = ['image', 'caption', 'display_order', 'uploaded_by']
    readonly_fields = ['uploaded_by']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'slug', 'is_verified', 'is_active',
        'member_count', 'created_by', 'created_at'
    ]
    list_filter = ['is_verified', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'contact_email']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'member_count', 'admin_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'logo', 'cover_image')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'website', 'social_links')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active', 'created_by')
        }),
        ('Statistics', {
            'fields': ('member_count', 'admin_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrganizationMemberInline, OrganizationGalleryInline]
    
    actions = ['mark_as_verified', 'mark_as_unverified', 'deactivate_organizations']
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} organizations marked as verified.')
    mark_as_verified.short_description = 'Mark selected organizations as verified'
    
    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} organizations marked as unverified.')
    mark_as_unverified.short_description = 'Mark selected organizations as unverified'
    
    def deactivate_organizations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} organizations deactivated.')
    deactivate_organizations.short_description = 'Deactivate selected organizations'


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'organization', 'role', 'is_active',
        'invited_by', 'joined_at'
    ]
    list_filter = ['role', 'is_active', 'joined_at']
    search_fields = [
        'user__username', 'user__email',
        'organization__name'
    ]
    readonly_fields = ['joined_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Member Information', {
            'fields': ('organization', 'user', 'role', 'permissions')
        }),
        ('Status', {
            'fields': ('is_active', 'invited_by')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_admin', 'make_member', 'deactivate_members']
    
    def make_admin(self, request, queryset):
        updated = queryset.update(role='ADMIN')
        self.message_user(request, f'{updated} members promoted to admin.')
    make_admin.short_description = 'Promote selected members to admin'
    
    def make_member(self, request, queryset):
        updated = queryset.update(role='MEMBER')
        self.message_user(request, f'{updated} members changed to regular member role.')
    make_member.short_description = 'Change selected to regular member role'
    
    def deactivate_members(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} members deactivated.')
    deactivate_members.short_description = 'Deactivate selected members'


@admin.register(OrganizationGallery)
class OrganizationGalleryAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'caption', 'display_order',
        'uploaded_by', 'created_at'
    ]
    list_filter = ['organization', 'created_at']
    search_fields = ['organization__name', 'caption']
    readonly_fields = ['created_at', 'updated_at', 'uploaded_by']
    
    fieldsets = (
        ('Gallery Image', {
            'fields': ('organization', 'image', 'caption', 'display_order')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
