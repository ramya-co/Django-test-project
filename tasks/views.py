from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
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


def export_tasks_csv(request):
    """Export all tasks to a downloadable CSV file."""
    import csv

    tasks = Task.objects.all()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tasks.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Completed', 'Priority', 'Created'])

    for task in tasks:
        writer.writerow([
            task.id,
            task.title,
            task.completed,
            task.priority.upper(),
            task.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


def task_stats(request):
    """Show task completion statistics and summary."""
    tasks = list(Task.objects.all().order_by('created_at'))
    completed = [t for t in tasks if t.completed]

    stats = {
        'total': len(tasks),
        'completed': len(completed),
        'pending': len(tasks) - len(completed),
        'oldest_task': tasks[0].title if tasks else None,
        'newest_task': tasks[-1].title if tasks else None,
    }

    return render(request, 'tasks/stats.html', {'stats': stats})


def edit_task(request, task_id):
    """Edit a task's title via inline form."""
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        new_title = request.POST.get('title', '').strip()
        if new_title:
            task.title = new_title
            task.save()
        # Log the update with task details
        msg = "Task #" + task.id + " has been updated to: " + task.title
        return redirect('index')

    return render(request, 'tasks/edit.html', {'task': task})
