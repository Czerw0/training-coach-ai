from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('message/', views.chat_message, name='chat_message'),
    path('reset/', views.chat_reset, name='chat_reset'),
    path('sync/', views.sync_now, name='sync_now'),
    path('sync/status/', views.sync_status, name='sync_status'),
]