from django import forms
from .models import Course, Stream, Subject, Resource
from .custom_widget import DragAndDropFileWidget

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
        fields = ['name', 'slug', 'resource_type', 'status', 'file', 'privacy', 'embed_link', 'description', 'subject', 'educational_year', 'meta_description', 'keywords', 'og_image']
        widgets = {
            'file': DragAndDropFileWidget(),
        }
