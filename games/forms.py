from django import forms

from games.models import BoardGame


class BoardGameSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=30,
        min_length=1,
        required=False,
        label='',
        widget=forms.TextInput(attrs={'placeholder': 'Search by game title...', 'class': 'form-control me-2'})
    )

class AddGameForm(forms.ModelForm):
    class Meta:
        model = BoardGame
        fields = [
            'title',
            'genre',
            'release_date',
            'rating',
            'min_players',
            'max_players',
            'description',
            'image_url',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Game Title'}),
            'genre': forms.Select(attrs={'class': 'form-control'}),
            'release_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '10'}),
            'min_players': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_players': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': '5', 'placeholder': 'Game Description'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Image URL (optional)'}),
        }
        labels = {
            'title': 'Заглавие',
            'genre': 'Жанр',
            'release_date': 'Дата на издаване',
            'rating': 'Рейтинг',
            'min_players': 'Минимален брой играчи',
            'max_players': 'Максимален брой играчи',
            'description': 'Описание',
        }

    def clean(self):
        cleaned_data = super().clean()
        min_players = cleaned_data.get('min_players')
        max_players = cleaned_data.get('max_players')
        rating = cleaned_data.get('rating')

        if min_players is not None and max_players is not None:
            if min_players > max_players:
                self.add_error('min_players', 'Минималният брой играчи не може да бъде по-голям от максималния.')
                self.add_error('max_players', 'Максималният брой играчи не може да бъде по-малък от минималния.')

        if rating is not None:
            if rating < 0 or rating > 5:
                self.add_error('rating', 'Скалата на рейтинга е от 0 до 5')

        return cleaned_data
