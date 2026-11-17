# Stock Waste Tracker — Streamlit

A mobile-friendly Streamlit stock wastage tracker with administrator login, optional staff accounts, product catalogue, weekly/monthly reports, staff and product summaries, and Excel export.

**Hosting:** Streamlit Community Cloud + Supabase Postgres.

See [SETUP.md](SETUP.md) for the complete setup and deployment guide. Run locally with:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Before running, configure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as Streamlit secrets or environment variables, and run `supabase_schema.sql` in your Supabase SQL Editor.
