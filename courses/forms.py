from django import forms
from .models import Course, Stream, Subject, Resource
from .custom_widget import DragAndDropFileWidget
from ckeditor.widgets import CKEditorWidget
from ckeditor.widgets import CKEditorWidget

class UniqueSlugForm(forms.ModelForm):
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if self.instance.pk:
            qs = self._meta.model.objects.exclude(pk=self.instance.pk)
        else:
            qs = self._meta.model.objects.all()
        if qs.filter(slug=slug).exists():
            raise forms.ValidationError(f"The slug '{slug}' is already in use. Please choose a different slug.")
        return slug

class CourseForm(UniqueSlugForm):
    class Meta:
        model = Course
        fields = '__all__'

class StreamForm(UniqueSlugForm):
    class Meta:
        model = Stream
        fields = '__all__'

class SubjectForm(UniqueSlugForm):
    class Meta:
        model = Subject
        fields = '__all__'


class ResourceForm(UniqueSlugForm):
    class Meta:
        model = Resource
        fields = ['name', 'slug', 'resource_type', 'status', 'file', 'resource_link', 'embed_link', 'content', 'privacy', 'description', 'subject', 'educational_year', 'meta_description', 'keywords', 'og_image']
        widgets = {
            'file': DragAndDropFileWidget(),
            'content': CKEditorWidget(),
        }
        help_texts = {
            'file': 'Upload a file (PDF, image, etc.)',
            'resource_link': 'Direct link to external resource (Google Drive, Dropbox, etc.)',
            'embed_link': 'YouTube video URL only',
            'content': 'Rich text content (use this for text-based resources)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        resource_link = cleaned_data.get('resource_link')
        embed_link = cleaned_data.get('embed_link')
        content = cleaned_data.get('content')
        
        if not file and not resource_link and not embed_link and not content:
            raise forms.ValidationError("Please provide at least one of: file upload, resource link, embed link (YouTube), or content.")
        
        return cleaned_data
