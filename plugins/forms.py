from django import forms
from plugins.models import Plugin

class PluginUploadForm(forms.Form):
    """Form for uploading a plugin"""
    plugin_file = forms.FileField(
        help_text="Upload a ZIP file containing the plugin",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
