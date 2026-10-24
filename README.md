# Galoul Service Informatique

Arabic/English Flask shop for computer sales, used-device purchase offers, repair requests, and online orders.

## 1) Run locally in VS Code

Install Python 3.10+.

Windows PowerShell:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ADMIN_USER="admin"
$env:ADMIN_PASSWORD="Choose-A-Strong-Password"
$env:SECRET_KEY="replace-with-a-long-random-secret"
python app.py
```
Open http://127.0.0.1:5000

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## 2) Before going live
- Change `ADMIN_USER`, `ADMIN_PASSWORD`, and `SECRET_KEY` in your hosting environment variables.
- Add your real WhatsApp number in `templates/base.html` by replacing `213000000000` with digits only, including Algeria country code 213 (no + or spaces).
- Replace the sample products and prices with your actual inventory from the admin dashboard.
- This starter uses SQLite. For deployment platforms with temporary disks, configure a persistent disk and set `DATABASE_PATH` to a path on that disk, or switch to a managed PostgreSQL database before relying on it for real orders.
- Use HTTPS hosting and back up the database regularly.
- Never publish your `.env`, passwords, or database file.

## 3) Deploy to Render (one possible host)
1. Create a GitHub account and a new private repository.
2. Upload these project files to the repository (do not upload `.venv`, `store.db`, passwords, or secrets).
3. Create a new Web Service on Render and connect the repository.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Add environment variables: `ADMIN_USER`, `ADMIN_PASSWORD`, `SECRET_KEY`.
7. Configure a persistent disk and `DATABASE_PATH` if keeping SQLite. For a business site, PostgreSQL is preferable.
8. Deploy, open the generated HTTPS URL, and test an order before sharing it with customers.

## Admin
Visit `/admin/login`. Defaults for local development are admin / ChangeMe123! unless environment variables are set. Change them before public deployment.
