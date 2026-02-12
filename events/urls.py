from django.urls import path

from events import views

app_name = 'events'

urlpatterns = [
    path('', views.events_list, name='events_list'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('join/<int:pk>/', views.join_event, name='join'),
    path('add/', views.add_event, name='add_event'),
]