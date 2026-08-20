from django import forms

from .models import AccessibilityPreference


class AccessibilityPreferenceForm(forms.ModelForm):
    LABELS = {
        'font_size': 'Tamaño del texto',
        'letter_spacing': 'Espacio entre letras',
        'word_spacing': 'Espacio entre palabras',
        'line_height': 'Interlineado',
        'high_contrast': 'Alto contraste',
        'reduce_motion': 'Reducir animaciones',
        'reading_guide': 'Guía de lectura',
        'text_to_speech_enabled': 'Lectura en voz alta',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = self.LABELS.get(name, field.label)
            css_class = 'form-check-input' if field.widget.input_type == 'checkbox' else 'form-control'
            field.widget.attrs['class'] = css_class

    class Meta:
        model = AccessibilityPreference
        fields = ('font_size', 'letter_spacing', 'word_spacing', 'line_height', 'high_contrast', 'reduce_motion', 'reading_guide', 'text_to_speech_enabled')
        widgets = {
            'font_size': forms.NumberInput(attrs={'min': 14, 'max': 28}),
            'letter_spacing': forms.NumberInput(attrs={'step': '0.1', 'min': 0, 'max': 1.5}),
            'word_spacing': forms.NumberInput(attrs={'step': '0.1', 'min': 0, 'max': 1.5}),
            'line_height': forms.NumberInput(attrs={'step': '0.1', 'min': 1.2, 'max': 2.4}),
        }
