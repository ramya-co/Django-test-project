from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
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


def task_report(request):
    """
    Generate a productivity report with task completion statistics,
    including average completion time and daily throughput.
    """
    tasks = list(Task.objects.all())

    if not tasks:
        return render(request, 'tasks/report.html', {'stats': None})

    total = len(tasks)
    completed = [t for t in tasks if t.completed]
    pending = [t for t in tasks if not t.completed]

    # Calculate average completion time in hours for finished tasks
    avg_completion_hours = 0
    if completed:
        from django.utils import timezone
        avg_completion_hours = sum(
            (t.completed_at - t.created_at).total_seconds() / 3600
            for t in completed
        ) / len(completed)

    stats = {
        'total': total,
        'completed_count': len(completed),
        'pending_count': len(pending),
        'completion_rate': round(len(completed) / total * 100, 1),
        'avg_completion_hours': round(avg_completion_hours, 1),
    }

    return render(request, 'tasks/report.html', {'stats': stats})
