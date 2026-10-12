# Cloud deployment

This project uses a Vercel-hosted React frontend, a Render-hosted Flask API, and a remotely accessible MySQL 8 database. Deploy the database and API before the frontend so the Vercel rewrite can point to the real API address.

## Environment variables

Set these on the Render backend service. Do not commit their values or place production credentials in a `.env` file in Git.

| Variable | Required | Description |
| --- | --- | --- |
| `DB_HOST` | Yes | Hostname for the MySQL service. |
| `DB_PORT` | No | MySQL port; defaults to `3306`. |
| `DB_USER` | Yes | MySQL application user. Use a dedicated user with access only to the project database. |
| `DB_PASSWORD` | Yes | Password for `DB_USER`. |
| `DB_NAME` | No | Database name; defaults to `college_team_finder`. |
| `JWT_SECRET` | Yes | Private signing key. The API refuses to start if it is missing. |
| `JWT_EXPIRY_HOURS` | No | Token lifetime in hours; defaults to `24`. |
| `PORT` | Set by Render | Public service port. `backend/gunicorn.conf.py` binds Gunicorn to `0.0.0.0:$PORT`; locally it defaults to `8000`. |

Create a strong JWT key locally with:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into Render's environment settings. Keep it private and use the same value across backend workers and restarts so existing tokens remain valid.

The frontend has no build-time API variable: it sends requests to `/api`, and Vercel forwards those requests to Render.

### Aiven MySQL settings

For the Aiven service provided for this deployment, set these Render variables from the Aiven Console's connection information:

| Variable | Value |
| --- | --- |
| `DB_HOST` | `mysql-326ce62d-team-finder.l.aivencloud.com` |
| `DB_PORT` | `19337` |
| `DB_USER` | `avnadmin` |
| `DB_NAME` | `college_team_finder` after importing the project schema (confirm the database exists in Aiven) |
| `DB_PASSWORD` | The password for `avnadmin`, entered privately in Render |

The matching interactive MySQL client command is:

```sh
mysql -h mysql-326ce62d-team-finder.l.aivencloud.com -P 19337 -u avnadmin -p --ssl-mode=REQUIRED
```

Enter the password when prompted; do not add it to this command, source control, or this repository. The backend uses MySQL Connector/Python, which negotiates TLS when the server supports it. Aiven requires encrypted connections; its console also provides a CA certificate if you want certificate and hostname verification configured for the client. Aiven recommends using that CA certificate for secure connections.

## 1. Create and initialize MySQL

Create or use a MySQL 8 database service that accepts connections from the Render backend. For the supplied Aiven service, use the settings in the Aiven section above. Keep the database and backend in nearby regions when possible.

Import `database/database.sql`, then `database/db_upgrades.sql`, once into a new, empty instance. The first file drops and recreates the `college_team_finder` database, so never run it against a database containing production data. The MySQL account used for the initial import must be allowed to create and drop the database. Give the runtime `DB_USER` only the privileges the application needs on that database.

If MySQL only allows connections from approved IP addresses, configure its network allowlist for the backend provider's outbound IPs or use a private network supported by both services.

## 2. Deploy the Flask API to Render

Create a Render Web Service from this repository. Use the repository root as the service root directory.

- Build command: `pip install -r backend/requirements.txt`
- Start command: `cd backend && gunicorn app:app --workers 2 --threads 4 --timeout 120`

Set the environment variables from the table above in Render. Render supplies `PORT`; the included Gunicorn config binds to that port and listens on all interfaces. The two workers each have a five-connection MySQL pool, for up to ten pooled application connections; make sure the database connection limit supports them.

After deploy, check `https://YOUR-BACKEND.onrender.com/api/health`. It should return `{"status":"ok"}`.

## 3. Point Vercel at the Render API

In `frontend/vercel.json`, replace `YOUR-BACKEND` with the actual Render service hostname. For example, a service named `team-finder-api` should use `https://team-finder-api.onrender.com/api/:path*` as the API rewrite destination. Keep the SPA rewrite to `/index.html` so direct navigation to React routes works.

Create a Vercel project from this repository and set its Root Directory to `frontend`. Use:

- Build command: `npm run build`
- Output directory: `dist`

Deploy, then open `/login`, sign in or create an account, and check protected pages and API-backed actions. Requests to `/api/...` will be forwarded through Vercel to Render.

## 4. Local production-server check

From PowerShell, install the backend requirements and run the same server command used by Render:

```powershell
cd backend
python -m pip install -r requirements.txt
gunicorn app:app --workers 2 --threads 4 --timeout 120
```

Set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `JWT_SECRET` in the process environment first. The local `.env` can supply them for development, but it is ignored by Git.

## Scaling notes

The supplied Gunicorn command runs two worker processes with four request threads each. The MySQL pool is created once per worker process. Increase workers or threads only after checking the hosting plan and MySQL connection limit; each additional worker creates another pool. For larger deployments, add monitoring and load testing before increasing concurrency.
