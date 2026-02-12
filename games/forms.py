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
