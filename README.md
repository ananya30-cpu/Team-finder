# Flask Backend

## Setup

1. Make sure MySQL is running and the project database has been loaded.
2. Create and activate a virtual environment, then install dependencies:

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DB_PASSWORD` and a private `JWT_SECRET` in `.env`, then run:

```powershell
python -m flask --app app run --debug --port 5000
```

The API base URL is `http://localhost:5000/api`.

## API overview

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/api/auth/login` | Sign in and receive a Bearer token |
| POST | `/api/auth/register` | Create an account with optional profile and skills |
| GET | `/api/me/dashboard` | Logged-in student's dashboard |
| GET / PUT | `/api/me/profile` | Read or update the logged-in student's profile |
| POST / PUT / DELETE | `/api/me/skills` | Manage the logged-in student's skills |
| PUT | `/api/me/password` | Change password |
| GET | `/api/students` | Search/filter students |
| GET / POST | `/api/projects` | Browse or create projects |
| PATCH | `/api/projects/<id>/status` | Update a creator's project status |
| GET / POST | `/api/join-requests` | List or send join requests |
| POST | `/api/join-requests/<id>/accept` | Accept a received request |
| POST | `/api/join-requests/<id>/reject` | Reject a received request |
| GET | `/api/stats` | Campus summary data |
| GET | `/api/connections` | Team connection graph data |

## Quick health check

```powershell
curl.exe http://localhost:5000/api/health
```
