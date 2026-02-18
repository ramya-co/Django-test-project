from django.urls import path

from . import views

urlpatterns = [
    path("sentry/", views.sentry_webhook, name="sentry_webhook"),
]
