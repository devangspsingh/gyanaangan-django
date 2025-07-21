from django import forms
from .models import StudentResult, ManualResultEntry


class RollNumberSearchForm(forms.Form):
    """Form for searching results by roll number"""
    
    roll_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
            'placeholder': 'Enter your roll number (e.g., 100220101)',
            'required': True
        }),
        label='Roll Number'
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
        }),
        label='I agree to the terms and conditions'
    )


class ManualMarksEntryForm(forms.ModelForm):
    """Form for manually entering marks"""
    
    class Meta:
        model = ManualResultEntry
        fields = ['roll_number', 'name']
        widgets = {
            'roll_number': forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
                'placeholder': 'Enter your roll number'
            }),
            'name': forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
                'placeholder': 'Enter your name (optional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form fields for each subject
        subjects = StudentResult.SUBJECTS_DATA['subjects']
        
        for i, subject in enumerate(subjects):
            subject_code = subject['code']
            subject_name = subject['name']
            credit = subject['credit']
            
            # Theory marks field
            if credit == 1:  # Lab subjects
                theory_max = 50
                internal_max = 50
                theory_label = f"{subject_name} - Practical Marks (Max: {theory_max})"
                internal_label = f"{subject_name} - Internal Marks (Max: {internal_max})"
            elif credit == 0:  # Non-credit
                theory_max = 50
                internal_max = 50
                theory_label = f"{subject_name} - Theory Marks (Max: {theory_max})"
                internal_label = f"{subject_name} - Internal Marks (Max: {internal_max})"
            else:  # Theory subjects
                theory_max = 70
                internal_max = 30
                theory_label = f"{subject_name} - External Marks (Max: {theory_max})"
                internal_label = f"{subject_name} - Internal Marks (Max: {internal_max})"
            
            # Theory/External marks
            self.fields[f'{subject_code}_theory'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=theory_max,
                widget=forms.NumberInput(attrs={
                    'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
                    'placeholder': f'0-{theory_max}'
                }),
                label=theory_label
            )
            
            # Internal marks
            self.fields[f'{subject_code}_internal'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=internal_max,
                widget=forms.NumberInput(attrs={
                    'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500',
                    'placeholder': f'0-{internal_max}'
                }),
                label=internal_label
            )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Process marks data
        marks_data = {}
        subjects = StudentResult.SUBJECTS_DATA['subjects']
        
        for subject in subjects:
            subject_code = subject['code']
            credit = subject['credit']
            
            theory = cleaned_data.get(f'{subject_code}_theory', 0) or 0
            internal = cleaned_data.get(f'{subject_code}_internal', 0) or 0
            
            marks_data[subject_code] = {
                'theory': theory,
                'internal': internal,
                'total': theory + internal,
                'credit': credit
            }
        
        cleaned_data['marks_data'] = marks_data
        return cleaned_data
