from django.forms.widgets import ClearableFileInput
from django.utils.safestring import mark_safe

class DragAndDropFileWidget(ClearableFileInput):
    template_name = 'widgets/drag_and_drop_file_widget.html'

    class Media:
        js = ('js/drag_and_drop.js',)
        css = {
            'all': ('css/drag_and_drop.css',)
        }

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(attrs, {
            'data-initial': bool(value),
            'data-initial-name': value.name if value else '',
            'data-initial-url': value.url if value else '',
        })
        html = super().render(name, value, attrs, renderer)
        initial_file_html = ''
        if value:
            initial_file_html = (
                f'<p class="text-gray-700">File: <span id="{attrs["id"]}-file-name">{value.name}</span></p>'
                f'<a id="{attrs["id"]}-file-link" href="{value.url}" class="text-blue-500" target="_blank">View File</a>'
            )
        else:
            initial_file_html = (
                f'<p class="text-gray-700">File: <span id="{attrs["id"]}-file-name"></span></p>'
                f'<a id="{attrs["id"]}-file-link" href="#" class="text-blue-500 hidden" target="_blank">View File</a>'
            )

        return mark_safe(
            '<div class="drag-and-drop-zone relative border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">'
            + html +
            '<div class="drop-area absolute inset-0 flex items-center justify-center bg-gray-100 opacity-75">'
            '<p class="text-gray-600">Drag & drop a file here or click to select a file.</p>'
            '</div></div>'
            f'<div id="{attrs["id"]}-file-details" class="file-details mt-4 text-center {"hidden" if not value else ""}">'
            + initial_file_html +
            '</div>'
        )
