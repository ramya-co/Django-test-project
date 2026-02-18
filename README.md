# Django To-Do List Web App

A simple, beginner-friendly Django web application for managing tasks. Built with Django 6.0.2 and SQLite database.

## Features

- ✅ Add new tasks
- 📋 View all tasks
- ✓ Mark tasks as complete/incomplete (with strike-through styling)
- 🗑️ Delete tasks
- 🔧 Admin panel for task management

## Requirements

- Python 3.8+
- Django 6.0.2

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ramya-co/Django-test-project.git
   cd Django-test-project
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser (for admin access):**
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create an admin account.

5. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - Main app: http://localhost:8000/
   - Admin panel: http://localhost:8000/admin/

## Project Structure

```
Django-test-project/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── todoproject/             # Project configuration
│   ├── __init__.py
│   ├── settings.py          # Project settings
│   ├── urls.py              # Main URL configuration
│   ├── asgi.py
│   └── wsgi.py
└── tasks/                   # Tasks application
    ├── __init__.py
    ├── admin.py             # Admin configuration
    ├── models.py            # Task model
    ├── views.py             # View functions
    ├── urls.py              # App URL configuration
    ├── migrations/          # Database migrations
    └── templates/           # HTML templates
        └── tasks/
            ├── base.html    # Base template with CSS
            └── index.html   # Main task list page
```

## Task Model

The `Task` model includes:
- **title** (CharField): Task description
- **completed** (BooleanField): Task completion status (default: False)
- **created_at** (DateTimeField): Timestamp when task was created

## Usage

### Adding a Task
1. Enter task description in the input field
2. Click "Add Task" button

### Marking a Task Complete
- Click the "Done" button next to a task
- Completed tasks appear with strike-through text
- Button changes to "Undo" for completed tasks

### Deleting a Task
- Click the "Delete" button next to any task

### Admin Panel
1. Log in at http://localhost:8000/admin/
2. Use your superuser credentials
3. Manage tasks with full CRUD operations
4. Filter tasks by completion status or creation date
5. Search tasks by title

## Screenshots

### Empty Task List
![Empty Task List](https://github.com/user-attachments/assets/1b5e87c3-5d91-46eb-a63d-a8c35f515a68)

### Tasks with Completion
![Completed Tasks](https://github.com/user-attachments/assets/aefeaae8-b978-4800-82d1-5fdba28f35d1)

### Admin Panel
![Admin Panel](https://github.com/user-attachments/assets/75f56cf6-1ebd-428a-84ca-9eb0877f5fa2)

## Technologies Used

- **Backend**: Django 6.0.2
- **Database**: SQLite (default Django database)
- **Frontend**: HTML5, CSS3
- **Authentication**: Django Admin (no user authentication for main app)

## License

This is a beginner tutorial project for learning Django.
