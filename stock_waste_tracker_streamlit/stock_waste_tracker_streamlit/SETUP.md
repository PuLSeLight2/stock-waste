# Stock Waste Tracker — Streamlit edition

This edition runs on Streamlit Community Cloud and stores data in Supabase Postgres. The database is separate from the app host, so records are not dependent on the app container's temporary filesystem.

## 1. Create the Supabase database

1. Create a free project at https://supabase.com/.
2. Open **SQL Editor** and run the contents of `supabase_schema.sql`.
3. Open **Project Settings → API** (or API Keys) and copy the Project URL and `service_role` secret key. Treat the service-role key like a password: never put it in GitHub or in the Python file.

The app uses the service-role key server-side to perform database operations. Keep the Streamlit app private to people you trust, and never share your Streamlit secrets.

## 2. Upload the app to GitHub

1. Create a GitHub account and a new repository (Private is recommended).
2. Upload `streamlit_app.py`, `requirements.txt`, and `supabase_schema.sql` to the repository. You may also upload this README/SETUP file.
3. Do **not** upload your Supabase service-role key or a `.streamlit/secrets.toml` file.

## 3. Deploy on Streamlit Community Cloud

1. Visit https://share.streamlit.io/ and sign in with GitHub.
2. Choose **Create app**, select your repository and `streamlit_app.py` as the main file.
3. In the app's **Settings → Secrets**, add the following TOML, replacing the example values:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR-SUPABASE-SERVICE-ROLE-KEY"
```

4. Save and deploy. Open the app's URL.
5. The first visitor sees **Create your administrator account**. Create your own username and a strong password. After that, the setup screen is replaced by login.

## 4. Add staff later

Sign in as administrator, open **User accounts**, and create staff logins. Staff accounts can record and view wastage; only admins see the user-management page. All accounts currently share the same operational access to wastage records.

## 5. Important security and data notes

- Keep the Supabase service-role key private. Anyone who obtains it can access or alter the database.
- Use a strong, unique administrator password. The app stores password hashes, not plain-text passwords.
- This is a lightweight internal tracker, not a formally audited enterprise identity system. Streamlit Community Cloud is public hosting; use a private GitHub repository and do not put confidential personal information in notes.
- Supabase free-plan quotas and Streamlit Community Cloud availability/limits can change. Check their current plan pages before relying on it for business-critical records.
- Export Excel backups regularly from the dashboard.

## Existing records

The original Flask version used a local `wastage.db` SQLite file. This Streamlit edition starts with a fresh Supabase database. If you already have records you need to preserve, do not delete the old database; ask for the migration script before switching over.
