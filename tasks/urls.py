from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.add_task, name='add_task'),
    path('toggle/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('export/', views.export_tasks_csv, name='export_tasks_csv'),
    path('stats/', views.task_stats, name='task_stats'),
    path('edit/<int:task_id>/', views.edit_task, name='edit_task'),
]
