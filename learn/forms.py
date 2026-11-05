from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class InstructorSignupForm(UserCreationForm):
    display_name = forms.CharField(max_length=120, label="Your name (shown to students)")
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")


class JoinCodeForm(forms.Form):
    code = forms.CharField(max_length=16, label="Class code")

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class JoinForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    consent = forms.BooleanField(
        label="I understand what is shared with my instructor and I agree.", required=True
    )


class RestoreForm(forms.Form):
    url = forms.CharField(label="Your personal learnmcp URL", max_length=300)
