from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.conf import settings
from django.http import HttpResponseForbidden
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


def trigger_test_crash(request):
    """
    Intentionally raises a ZeroDivisionError so Sentry captures a real
    event and fires the webhook to kick off the full triage pipeline.
    Remove this view after end-to-end testing is complete.
    """
    if not settings.DEBUG:
        return HttpResponseForbidden("This debug endpoint is only available in DEBUG mode")
    # Simulate a realistic crash in a task-processing function
    task_count = Task.objects.filter(completed=False).count()
    result = 1 / 0  # noqa: intentional ZeroDivisionError for pipeline testing
    return redirect('index')
