from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from PIL import Image
import io
from .models import SEODetail, Banner

@admin.register(SEODetail)
class SEODetailAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'title', 'meta_description', 'og_image', 'site_name')
    search_fields = ('page_name', 'title')


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'image_preview',
        'is_primary',
        'is_active',
        'status_badge',
        'active_from',
        'active_until_display',
        'display_order',
        'view_count',
        'click_count',
    )
    list_filter = ('is_active', 'is_primary', 'active_from', 'active_until')
    search_fields = ('title', 'description', 'link_text')
    readonly_fields = (
        'image_preview_with_ratio',
        'image_cropper_tool',
        'image_dimensions_info',
        'mobile_image_preview_with_ratio',
        'mobile_image_cropper_tool',
        'mobile_image_dimensions_info',
        'view_count',
        'click_count',
        'created_at',
        'updated_at',
        'is_currently_active'
    )
    
    class Media:
        css = {
            'all': (
                'admin/css/banner_admin.css',
                'https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css',
            )
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js',
            'admin/js/banner_cropper.js',
        )
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description')
        }),
        ('Desktop Banner Image (Recommended: 1600x324px)', {
            'fields': ('image', 'image_preview_with_ratio', 'image_cropper_tool', 'image_dimensions_info'),
            'description': '<strong>Important:</strong> Upload an image with aspect ratio 1600:324 (approximately 4.94:1). Use the cropper tool below to adjust your image.'
        }),
        ('Mobile Banner Image (Recommended: 1600x648px)', {
            'fields': ('mobile_image', 'mobile_image_preview_with_ratio', 'mobile_image_cropper_tool', 'mobile_image_dimensions_info'),
            'description': '<strong>Mobile Image:</strong> Same width (1600px) but double height (648px) for better mobile display. If not provided, desktop image will be used.'
        }),
        ('Link Settings', {
            'fields': ('link_url', 'link_text')
        }),
        ('Display Settings', {
            'fields': ('is_primary', 'is_active', 'display_order')
        }),
        ('Schedule', {
            'fields': ('active_from', 'active_until'),
            'description': 'Set when this banner should be visible to users. Leave "Active Until" empty for permanent display.'
        }),
        ('Analytics', {
            'fields': ('view_count', 'click_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['display_order', '-is_primary', '-created_at']
    list_editable = ('is_active', 'display_order')
    actions = ['activate_banners', 'deactivate_banners', 'set_as_primary']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Preview"

    def get_image_dimensions(self, image_field):
        """Helper method to get image dimensions."""
        try:
            if image_field and hasattr(image_field, 'path'):
                with Image.open(image_field.path) as img:
                    return img.size  # Returns (width, height)
        except Exception as e:
            print(f"Error reading image dimensions: {e}")
        return None

    def image_preview_with_ratio(self, obj):
        """Display image with aspect ratio overlay and crop suggestions."""
        if not obj.image:
            return format_html(
                '<div style="padding: 20px; background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; text-align: center;">'
                '<p style="color: #6c757d; margin: 0;">No image uploaded yet</p>'
                '<p style="color: #6c757d; font-size: 12px; margin: 5px 0 0 0;">Recommended: 1600x324px (aspect ratio 4.94:1)</p>'
                '</div>'
            )
        
        dimensions = self.get_image_dimensions(obj.image)
        if not dimensions:
            return format_html(
                '<img src="{}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        
        width, height = dimensions
        actual_ratio = width / height if height > 0 else 0
        target_ratio = 1600 / 324  # 4.938...
        ratio_diff = abs(actual_ratio - target_ratio)
        
        # Determine status and styling
        if ratio_diff < 0.01:  # Very close to target
            status_color = '#28a745'
            status_icon = '✓'
            status_text = 'Perfect Ratio'
            border_color = '#28a745'
        elif ratio_diff < 0.5:  # Acceptable
            status_color = '#ffc107'
            status_icon = '⚠'
            status_text = 'Acceptable Ratio'
            border_color = '#ffc107'
        else:  # Needs adjustment
            status_color = '#dc3545'
            status_icon = '✕'
            status_text = 'Needs Cropping'
            border_color = '#dc3545'
        
        # Calculate suggested crop dimensions
        if actual_ratio > target_ratio:
            # Image is too wide, crop width
            new_width = int(height * target_ratio)
            crop_suggestion = f"Crop to {new_width}x{height}px (remove {width - new_width}px from width)"
        else:
            # Image is too tall, crop height
            new_height = int(width / target_ratio)
            crop_suggestion = f"Crop to {width}x{new_height}px (remove {height - new_height}px from height)"
        
        return format_html(
            '<div style="border: 3px solid {}; border-radius: 8px; padding: 10px; background: #f8f9fa;">'
            '<div style="position: relative; margin-bottom: 10px;">'
            '<img src="{}" style="width: 100%; max-width: 800px; height: auto; display: block; border-radius: 4px;" />'
            '<div style="position: absolute; top: 10px; right: 10px; background: {}; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;">'
            '{} {}'
            '</div>'
            '</div>'
            '<div style="background: white; padding: 12px; border-radius: 4px; margin-top: 10px;">'
            '<p style="margin: 5px 0; font-weight: bold;">Current Dimensions: {}x{}px</p>'
            '<p style="margin: 5px 0;">Current Aspect Ratio: <strong>{:.2f}:1</strong></p>'
            '<p style="margin: 5px 0;">Target Aspect Ratio: <strong>4.94:1</strong> (1600x324px)</p>'
            '<p style="margin: 5px 0; color: {}; font-weight: bold;">{}</p>'
            '{}'
            '</div>'
            '</div>',
            border_color,
            obj.image.url,
            status_color,
            status_icon,
            status_text,
            width,
            height,
            actual_ratio,
            status_color,
            status_text,
            format_html(
                '<p style="margin: 5px 0; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 4px;">'
                '<strong>💡 Crop Suggestion:</strong> {}'
                '</p>',
                crop_suggestion
            ) if ratio_diff >= 0.01 else ''
        )
    image_preview_with_ratio.short_description = "Banner Preview"

    def image_cropper_tool(self, obj):
        """Interactive image cropper tool with 1600:324 aspect ratio."""
        if not obj.image:
            return format_html(
                '<div style="padding: 20px; background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; text-align: center;">'
                '<p style="color: #856404; margin: 0; font-weight: bold;">📸 Upload an image first to use the cropper tool</p>'
                '</div>'
            )
        
        return format_html(
            '<div id="banner-cropper-container" style="background: white; padding: 20px; border-radius: 8px; border: 2px solid #2196F3;">'
            '<div style="margin-bottom: 15px;">'
            '<h3 style="margin: 0 0 10px 0; color: #1976D2;">✂️ Image Cropper Tool</h3>'
            '<p style="margin: 0; color: #666;">Adjust the crop area below to match the 1600:324 aspect ratio (4.94:1)</p>'
            '</div>'
            
            '<!-- Original Image for Cropping -->'
            '<div style="max-width: 100%; overflow: hidden; margin-bottom: 15px;">'
            '<img id="banner-image-to-crop" src="{}" style="max-width: 100%; display: block;" />'
            '</div>'
            
            '<!-- Cropper Controls -->'
            '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 4px;">'
            '<button type="button" id="crop-zoom-in" class="button" style="background: #2196F3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '🔍 Zoom In'
            '</button>'
            '<button type="button" id="crop-zoom-out" class="button" style="background: #2196F3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '🔍 Zoom Out'
            '</button>'
            '<button type="button" id="crop-rotate-left" class="button" style="background: #2196F3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '↺ Rotate Left'
            '</button>'
            '<button type="button" id="crop-rotate-right" class="button" style="background: #2196F3; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '↻ Rotate Right'
            '</button>'
            '<button type="button" id="crop-reset" class="button" style="background: #757575; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '🔄 Reset'
            '</button>'
            '</div>'
            
            '<!-- Crop Info Display -->'
            '<div id="crop-info" style="padding: 12px; background: #e3f2fd; border-radius: 4px; margin-bottom: 15px; font-family: monospace; font-size: 13px;">'
            '<strong>Current Crop Area:</strong> <span id="crop-dimensions">Select crop area...</span>'
            '</div>'
            
            '<!-- Download Button -->'
            '<div style="text-align: center;">'
            '<button type="button" id="crop-download" class="button" style="background: #4CAF50; color: white; border: none; padding: 12px 32px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold;">'
            '⬇️ Download Cropped Image (1600x324px)'
            '</button>'
            '<p style="margin: 10px 0 0 0; color: #666; font-size: 13px;">'
            'After downloading, re-upload the cropped image in the "Image" field above'
            '</p>'
            '</div>'
            
            '<!-- Hidden data -->'
            '<input type="hidden" id="banner-image-url" value="{}" />'
            '<input type="hidden" id="banner-id" value="{}" />'
            '</div>',
            obj.image.url,
            obj.image.url,
            obj.id
        )
    image_cropper_tool.short_description = "Interactive Cropper (1600x324)"

    def image_dimensions_info(self, obj):
        """Display detailed image information and cropping guide."""
        if not obj.image:
            return "Upload an image first"
        
        dimensions = self.get_image_dimensions(obj.image)
        if not dimensions:
            return "Could not read image dimensions"
        
        width, height = dimensions
        actual_ratio = width / height if height > 0 else 0
        target_ratio = 1600 / 324
        
        return format_html(
            '<div style="background: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; border-radius: 4px; font-family: monospace;">'
            '<h4 style="margin: 0 0 10px 0; color: #1976D2;">📐 Image Dimensions Guide</h4>'
            '<table style="width: 100%; border-collapse: collapse;">'
            '<tr><td style="padding: 5px; font-weight: bold;">Current Size:</td><td style="padding: 5px;">{} x {} pixels</td></tr>'
            '<tr><td style="padding: 5px; font-weight: bold;">Current Ratio:</td><td style="padding: 5px;">{:.4f}:1</td></tr>'
            '<tr><td style="padding: 5px; font-weight: bold;">Target Ratio:</td><td style="padding: 5px;">{:.4f}:1 (1600:324)</td></tr>'
            '<tr><td style="padding: 5px; font-weight: bold;">Difference:</td><td style="padding: 5px; color: {};">{:+.4f}</td></tr>'
            '</table>'
            '<div style="margin-top: 15px; padding: 10px; background: white; border-radius: 4px;">'
            '<p style="margin: 0; font-weight: bold; color: #1976D2;">🎯 Recommended Tools for Cropping:</p>'
            '<ul style="margin: 5px 0; padding-left: 20px;">'
            '<li><a href="https://www.canva.com" target="_blank">Canva</a> - Set custom dimensions to 1600x324px</li>'
            '<li><a href="https://www.photopea.com" target="_blank">Photopea</a> - Free Photoshop alternative</li>'
            '<li><a href="https://squoosh.app" target="_blank">Squoosh</a> - Resize and optimize</li>'
            '<li>Photoshop/GIMP - Crop tool with aspect ratio 1600:324</li>'
            '</ul>'
            '</div>'
            '</div>',
            width,
            height,
            actual_ratio,
            target_ratio,
            '#dc3545' if abs(actual_ratio - target_ratio) > 0.01 else '#28a745',
            actual_ratio - target_ratio
        )
    image_dimensions_info.short_description = "Dimensions Info & Crop Guide"

    # Mobile Image Methods
    def mobile_image_preview_with_ratio(self, obj):
        """Display mobile image with aspect ratio overlay and crop suggestions."""
        if not obj.mobile_image:
            return format_html(
                '<div style="padding: 20px; background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; text-align: center;">'
                '<p style="color: #6c757d; margin: 0;">No mobile image uploaded</p>'
                '<p style="color: #6c757d; font-size: 12px; margin: 5px 0 0 0;">Recommended: 1600x648px (aspect ratio 2.47:1)</p>'
                '<p style="color: #6c757d; font-size: 11px; margin: 5px 0 0 0;">If not provided, desktop image will be used on mobile</p>'
                '</div>'
            )
        
        dimensions = self.get_image_dimensions(obj.mobile_image)
        if not dimensions:
            return format_html(
                '<img src="{}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.mobile_image.url
            )
        
        width, height = dimensions
        actual_ratio = width / height if height > 0 else 0
        target_ratio = 1600 / 648  # 2.469...
        ratio_diff = abs(actual_ratio - target_ratio)
        
        # Determine status and styling
        if ratio_diff < 0.01:  # Very close to target
            status_color = '#28a745'
            status_icon = '✓'
            status_text = 'Perfect Ratio'
            border_color = '#28a745'
        elif ratio_diff < 0.5:  # Acceptable
            status_color = '#ffc107'
            status_icon = '⚠'
            status_text = 'Acceptable Ratio'
            border_color = '#ffc107'
        else:  # Needs adjustment
            status_color = '#dc3545'
            status_icon = '✕'
            status_text = 'Needs Cropping'
            border_color = '#dc3545'
        
        # Calculate suggested crop dimensions
        if actual_ratio > target_ratio:
            # Image is too wide, crop width
            new_width = int(height * target_ratio)
            crop_suggestion = f"Crop to {new_width}x{height}px (remove {width - new_width}px from width)"
        else:
            # Image is too tall, crop height
            new_height = int(width / target_ratio)
            crop_suggestion = f"Crop to {width}x{new_height}px (remove {height - new_height}px from height)"
        
        return format_html(
            '<div style="border: 3px solid {}; border-radius: 8px; padding: 10px; background: #f8f9fa;">'
            '<div style="position: relative; margin-bottom: 10px;">'
            '<img src="{}" style="width: 100%; max-width: 800px; height: auto; display: block; border-radius: 4px;" />'
            '<div style="position: absolute; top: 10px; right: 10px; background: {}; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;">'
            '{} {}'
            '</div>'
            '</div>'
            '<div style="background: white; padding: 12px; border-radius: 4px; margin-top: 10px;">'
            '<p style="margin: 5px 0; font-weight: bold;">Current Dimensions: {}x{}px</p>'
            '<p style="margin: 5px 0;">Current Aspect Ratio: <strong>{:.2f}:1</strong></p>'
            '<p style="margin: 5px 0;">Target Aspect Ratio: <strong>2.47:1</strong> (1600x648px)</p>'
            '<p style="margin: 5px 0; color: {}; font-weight: bold;">{}</p>'
            '{}'
            '</div>'
            '</div>',
            border_color,
            obj.mobile_image.url,
            status_color,
            status_icon,
            status_text,
            width,
            height,
            actual_ratio,
            status_color,
            status_text,
            format_html(
                '<p style="margin: 5px 0; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 4px;">'
                '<strong>💡 Crop Suggestion:</strong> {}'
                '</p>',
                crop_suggestion
            ) if ratio_diff >= 0.01 else ''
        )
    mobile_image_preview_with_ratio.short_description = "Mobile Banner Preview"

    def mobile_image_cropper_tool(self, obj):
        """Interactive image cropper tool with 1600:648 aspect ratio for mobile."""
        if not obj.mobile_image:
            return format_html(
                '<div style="padding: 20px; background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; text-align: center;">'
                '<p style="color: #856404; margin: 0; font-weight: bold;">📱 Upload a mobile image first to use the cropper tool</p>'
                '</div>'
            )
        
        return format_html(
            '<div id="banner-mobile-cropper-container" style="background: white; padding: 20px; border-radius: 8px; border: 2px solid #FF9800;">'
            '<div style="margin-bottom: 15px;">'
            '<h3 style="margin: 0 0 10px 0; color: #F57C00;">✂️ Mobile Image Cropper Tool</h3>'
            '<p style="margin: 0; color: #666;">Adjust the crop area below to match the 1600:648 aspect ratio (2.47:1)</p>'
            '</div>'
            
            '<!-- Original Image for Cropping -->'
            '<div style="max-width: 100%; overflow: hidden; margin-bottom: 15px;">'
            '<img id="banner-mobile-image-to-crop" src="{}" style="max-width: 100%; display: block;" />'
            '</div>'
            
            '<!-- Cropper Controls -->'
            '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 4px;">'
            '<button type="button" id="mobile-crop-zoom-in" class="button" style="background: #FF9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '🔍 Zoom In'
            '</button>'
            '<button type="button" id="mobile-crop-zoom-out" class="button" style="background: #FF9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '🔍 Zoom Out'
            '</button>'
            '<button type="button" id="mobile-crop-rotate-left" class="button" style="background: #FF9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '↺ Rotate Left'
            '</button>'
            '<button type="button" id="mobile-crop-rotate-right" class="button" style="background: #FF9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '↻ Rotate Right'
            '</button>'
            '<button type="button" id="mobile-crop-reset" class="button" style="background: #757575; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">'
            '🔄 Reset'
            '</button>'
            '</div>'
            
            '<!-- Crop Info Display -->'
            '<div id="mobile-crop-info" style="padding: 12px; background: #fff3e0; border-radius: 4px; margin-bottom: 15px; font-family: monospace; font-size: 13px;">'
            '<strong>Current Crop Area:</strong> <span id="mobile-crop-dimensions">Select crop area...</span>'
            '</div>'
            
            '<!-- Download Button -->'
            '<div style="text-align: center;">'
            '<button type="button" id="mobile-crop-download" class="button" style="background: #FF9800; color: white; border: none; padding: 12px 32px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold;">'
            '⬇️ Download Cropped Mobile Image (1600x648px)'
            '</button>'
            '<p style="margin: 10px 0 0 0; color: #666; font-size: 13px;">'
            'After downloading, re-upload the cropped image in the "Mobile Image" field above'
            '</p>'
            '</div>'
            
            '<!-- Hidden data -->'
            '<input type="hidden" id="banner-mobile-image-url" value="{}" />'
            '</div>',
            obj.mobile_image.url,
            obj.mobile_image.url
        )
    mobile_image_cropper_tool.short_description = "Interactive Mobile Cropper (1600x648)"

    def mobile_image_dimensions_info(self, obj):
        """Display detailed mobile image information and cropping guide."""
        if not obj.mobile_image:
            return "Upload a mobile image first"
        
        dimensions = self.get_image_dimensions(obj.mobile_image)
        if not dimensions:
            return "Could not read image dimensions"
        
        width, height = dimensions
        actual_ratio = width / height if height > 0 else 0
        target_ratio = 1600 / 648
        
        return format_html(
            '<div style="background: #fff3e0; border-left: 4px solid #FF9800; padding: 15px; border-radius: 4px; font-family: monospace;">'
            '<h4 style="margin: 0 0 10px 0; color: #F57C00;">📱 Mobile Image Dimensions Guide</h4>'
            '<table style="width: 100%; border-collapse: collapse;">'
            '<tr><td style="padding: 5px; font-weight: bold;">Current Size:</td><td style="padding: 5px;">{} x {} pixels</td></tr>'
            '<tr><td style="padding: 5px; font-weight: bold;">Current Ratio:</td><td style="padding: 5px;">{:.4f}:1</td></tr>'
            '<tr><td style="padding: 5px; font-weight: bold;">Target Ratio:</td><td style="padding: 5px;">{:.4f}:1 (1600:648)</td></tr>'
            '<tr><td style="padding: 5px; font-weight: bold;">Difference:</td><td style="padding: 5px; color: {};">{:+.4f}</td></tr>'
            '</table>'
            '<div style="margin-top: 15px; padding: 10px; background: white; border-radius: 4px;">'
            '<p style="margin: 0; font-weight: bold; color: #F57C00;">📱 Why Mobile Image?</p>'
            '<p style="margin: 5px 0; font-size: 13px;">Mobile images have double the height (648px vs 324px) to display better on portrait-oriented mobile screens.</p>'
            '</div>'
            '</div>',
            width,
            height,
            actual_ratio,
            target_ratio,
            '#dc3545' if abs(actual_ratio - target_ratio) > 0.01 else '#28a745',
            actual_ratio - target_ratio
        )
    mobile_image_dimensions_info.short_description = "Mobile Dimensions Info"

    def mobile_image_preview(self, obj):
        if obj.mobile_image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 150px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.mobile_image.url
            )
        return "No Mobile Image (Will use desktop image)"
    mobile_image_preview.short_description = "Mobile Image Preview"

    def active_until_display(self, obj):
        """Display active_until with special formatting for None (permanent)."""
        if obj.active_until is None:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">∞ Permanent</span>'
            )
        return obj.active_until.strftime('%Y-%m-%d %H:%M:%S') if obj.active_until else '-'
    active_until_display.short_description = "Active Until"
    active_until_display.admin_order_field = 'active_until'

    def status_badge(self, obj):
        if obj.is_currently_active():
            expiry_text = "LIVE" if obj.active_until else "LIVE ∞"
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">● {}</span>',
                expiry_text
            )
        now = timezone.now()
        if obj.active_from > now:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">⏳ SCHEDULED</span>'
            )
        if obj.active_until and obj.active_until < now:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">✓ EXPIRED</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">✕ INACTIVE</span>'
        )
    status_badge.short_description = "Status"

    def activate_banners(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} banner(s) activated successfully.")
    activate_banners.short_description = "Activate selected banners"

    def deactivate_banners(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} banner(s) deactivated successfully.")
    deactivate_banners.short_description = "Deactivate selected banners"

    def set_as_primary(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "Please select only one banner to set as primary.", level='error')
            return
        banner = queryset.first()
        Banner.objects.filter(is_primary=True).update(is_primary=False)
        banner.is_primary = True
        banner.save()
        self.message_user(request, f"'{banner.title}' is now the primary banner.")
    set_as_primary.short_description = "Set as primary banner"
