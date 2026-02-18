from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from .models import Task

def index(request):
    """Display all tasks"""
    tasks = Task.objects.all()
    return render(request, 'tasks/index.html', {'tasks': tasks})

@require_POST
def add_task(request):
    """Add a new task"""
    title = request.POST.get('title', '').strip()
    if title:
        Task.objects.create(title=title)
    return redirect('index')

@require_POST
def toggle_task(request, task_id):
    """Mark a task as complete or incomplete"""
    task = get_object_or_404(Task, id=task_id)
    task.completed = not task.completed
    task.save()
    return redirect('index')

@require_POST
def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('index')
