from django import forms

from .models import Activity


class ActivityAnswerForm(forms.Form):
    answer = forms.CharField(widget=forms.HiddenInput())
