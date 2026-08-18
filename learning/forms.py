from django import forms

from .models import AccessibilityPreference


class AccessibilityPreferenceForm(forms.ModelForm):
    class Meta:
        model = AccessibilityPreference
        fields = ('font_size', 'letter_spacing', 'word_spacing', 'line_height', 'high_contrast', 'reduce_motion', 'reading_guide', 'text_to_speech_enabled')
        widgets = {
            'font_size': forms.NumberInput(attrs={'min': 14, 'max': 28}),
            'letter_spacing': forms.NumberInput(attrs={'step': '0.1', 'min': 0, 'max': 1.5}),
            'word_spacing': forms.NumberInput(attrs={'step': '0.1', 'min': 0, 'max': 1.5}),
            'line_height': forms.NumberInput(attrs={'step': '0.1', 'min': 1.2, 'max': 2.4}),
        }
