# Employee Leave Management System

**Institution:** Islamic University in Uganda (IUIU)  
**Programme:** Bachelor of Information Technology  
**Course:** BIT 3105 – Web Programming  
**Academic Level:** Year 3, Semester 1  
**Session:** Evening

## Group Members

| No. | Full Name | Registration Number |
|---|---|---|
| 1 | ANOOR ABDALLAH | 224-063011-29015 |
| 2 | NAGAWA SHADIA DANIELLA | 224-063012-29541 |
| 3 | SHUKURAN FIRIDAUS SABR | 224-063012-29543 |
| 4 | ATUGUMYA GILBERT | 225-063012-37715 |

## Project Overview

The Employee Leave Management System is a Django-based web application designed to help an organization manage employee leave requests. Employees can submit leave applications and track their status, while authorized personnel can review applications and maintain employee and leave records.

## Main Features

- User authentication and access control
- Employee, department, and team-size management
- Leave type management
- Employee leave applications and status tracking
- Leave application review and processing
- Leave records and administrative management
- Django administration interface

## Technologies Used

- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Backend:** Python, Django
- **Database (local development):** SQLite
- **Editor:** Visual Studio Code

## Project Structure

```text
general_settings/   Django project settings and root URL configuration
leave/              Django application (models, views, forms, templates, static assets)
docs/               Project documentation
manage.py           Django management entry point
requirements.txt    Python package dependencies
db.sqlite3          Local SQLite database (not committed to Git)
setup_project.bat   Windows setup helper
run_project.bat     Windows run helper
```

## Running the Project Locally (Windows)

Open a terminal in the folder containing `manage.py` and run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Visit **http://127.0.0.1:8000/** in your browser.

To create an administrator account on a new local database, run:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Then visit **http://127.0.0.1:8000/admin/**. Do not commit credentials or environment secrets to GitHub.

## Deployment

The online deployment link will be added after the project is successfully hosted and tested.

## Academic Purpose

This project was developed for **BIT 3105 Web Programming**, Year 3 Semester 1 (Evening Session), at the Islamic University in Uganda.
