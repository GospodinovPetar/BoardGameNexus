from django import forms
from django.core.exceptions import ValidationError

from .models import GameReview, UserCollection, VenueReview


class ReviewForm(forms.ModelForm):
    class Meta:
        model = GameReview
        fields = ["title", "content", "rating"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Give your review a title",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Share your thoughts...",
                }
            ),
            "rating": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 5,
                }
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None or rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5.")
        return rating


class VenueReviewForm(forms.ModelForm):
    class Meta:
        model = VenueReview
        fields = ["title", "content", "rating"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Summarize your visit",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "How was the space, staff, and game selection?",
                }
            ),
            "rating": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 5,
                }
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None or rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5.")
        return rating


class UserCollectionForm(forms.ModelForm):
    class Meta:
        model = UserCollection
        fields = ["status", "notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional notes...",
                }
            ),
        }
