from django.contrib import admin

from .models import GameReview, UserCollection, VenueReview

admin.site.register(GameReview)
admin.site.register(UserCollection)
admin.site.register(VenueReview)
