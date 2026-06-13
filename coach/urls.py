from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('message/', views.chat_message, name='chat_message'),
    path('reset/', views.chat_reset, name='chat_reset'),
]