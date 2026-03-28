from django.test import TestCase
from django.urls import reverse
from tasks.models import Task


class ExportTasksCSVViewTests(TestCase):
    """Tests for the CSV export view."""

    def test_export_with_zero_tasks_returns_200(self):
        """Export with empty database must not raise ZeroDivisionError."""
        response = self.client.get(reverse('export_tasks_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Completion rate: 0%', content)

    def test_export_with_tasks_none_completed_shows_zero_percent(self):
        """Export with tasks but none completed shows 0.0% completion rate."""
        Task.objects.create(title='Task 1', completed=False)
        Task.objects.create(title='Task 2', completed=False)
        response = self.client.get(reverse('export_tasks_csv'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Completion rate: 0.0%', content)

    def test_export_with_some_tasks_completed_calculates_rate(self):
        """Export with 2 of 4 tasks completed shows 50.0% completion rate."""
        Task.objects.create(title='Task 1', completed=True)
        Task.objects.create(title='Task 2', completed=False)
        Task.objects.create(title='Task 3', completed=True)
        Task.objects.create(title='Task 4', completed=False)
        response = self.client.get(reverse('export_tasks_csv'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Completion rate: 50.0%', content)

    def test_export_with_all_tasks_completed_shows_hundred_percent(self):
        """Export with all tasks completed shows 100.0% completion rate."""
        Task.objects.create(title='Done 1', completed=True)
        Task.objects.create(title='Done 2', completed=True)
        response = self.client.get(reverse('export_tasks_csv'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Completion rate: 100.0%', content)

    def test_export_includes_csv_headers(self):
        """CSV export includes proper column headers."""
        response = self.client.get(reverse('export_tasks_csv'))
        content = response.content.decode('utf-8')
        self.assertIn('ID,Title,Completed,Created At', content)
