from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('message/', views.chat_message, name='chat_message'),
    path('reset/', views.chat_reset, name='chat_reset'),
    path('calendar/', views.calendar_page, name='calendar_page'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('calendar/session/', views.save_planned_session, name='save_planned_session'),
    path('calendar/session/delete/', views.delete_planned_session, name='delete_planned_session'),
]