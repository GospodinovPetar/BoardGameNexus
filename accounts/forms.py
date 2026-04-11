from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import CustomUser, UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].widget.attrs.setdefault("class", "form-control")
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_email(self):
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["password"].widget.attrs["class"] = "form-control"
        self.helper = FormHelper()
        self.helper.form_tag = False


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "bio",
            "avatar",
            "date_of_birth",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.setdefault("class", "form-control")
        self.fields["last_name"].widget.attrs.setdefault("class", "form-control")
        self.fields["email"].widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = CustomUser.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This email is already registered.")
        return email


class EditUserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["favourite_genre", "games_played", "location"]
        widgets = {
            "favourite_genre": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["games_played"].widget = forms.NumberInput(
            attrs={"class": "form-control"}
        )
        self.fields["games_played"].disabled = True
