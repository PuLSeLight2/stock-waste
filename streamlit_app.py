import os
from datetime import date, datetime, timedelta
from io import BytesIO
from collections import defaultdict

import pandas as pd
import streamlit as st
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Stock Waste Tracker", page_icon="📦", layout="wide")
CATEGORIES = ["Spirit", "Draught", "Wine", "Soft drink", "Snacks", "Bottle beer/cider", "Alcopops"]
UNITS = ["units", "ml", "cl", "litres", "pints", "half pints", "bottles", "cans", "kegs", "portions", "bags"]
STARTER = {
    "Draught": ["Carling", "Coors", "Stowford Press", "Guinness", "Birra Moretti"],
    "Bottle beer/cider": ["Corona", "Peroni", "Budweiser", "Rekorderlig", "Stella Artois"],
    "Alcopops": ["WKD Blue", "Smirnoff Ice", "Bacardi Breezer"],
    "Soft drink": ["Coca-Cola", "Diet Coke", "Lemonade", "Orange Juice", "Water"],
    "Spirit": ["Vodka", "Gin", "Rum", "Whisky", "Tequila", "Brandy"],
    "Wine": ["House red", "House white", "House rosé", "Prosecco"],
    "Snacks": ["Crisps", "Peanuts", "Chocolate"],
}


def get_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name)


@st.cache_resource
def supabase_client() -> Client:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase settings are missing. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to Streamlit secrets.")
    return create_client(url, key)


try:
    sb = supabase_client()
except Exception as exc:
    st.title("📦 Stock Waste Tracker")
    st.error(str(exc))
    st.info("Follow SETUP.md in the download to create your database and add your Supabase secrets.")
    st.stop()


def rows(table, order=None):
    q = sb.table(table).select("*")
    if order:
        q = q.order(order, desc=True)
    return q.execute().data or []


def fmt(n):
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def ensure_catalogue():
    existing = {(p["category"], p["name"]) for p in rows("products")}
    missing = [{"category": c, "name": n} for c, names in STARTER.items() for n in names if (c, n) not in existing]
    if missing:
        sb.table("products").insert(missing).execute()


def sign_in(user):
    st.session_state.user = {"id": user["id"], "username": user["username"], "role": user["role"]}


def auth_screen():
    users = rows("users")
    st.title("📦 Stock Waste Tracker")
    st.caption("Secure stock wastage recording and reporting")
    if not users:
        st.subheader("Create your administrator account")
        with st.form("first_admin"):
            username = st.text_input("Username")
            pw = st.text_input("Password", type="password", help="Use at least 10 characters.")
            confirm = st.text_input("Confirm password", type="password")
            go = st.form_submit_button("Create administrator", type="primary", use_container_width=True)
        if go:
            if len(username.strip()) < 3 or len(pw) < 10:
                st.error("Username must be at least 3 characters and password at least 10 characters.")
            elif pw != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    user = sb.table("users").insert({"username": username.strip(), "password_hash": generate_password_hash(pw), "role": "admin"}).execute().data[0]
                    sign_in(user); st.rerun()
                except Exception:
                    st.error("That username may already exist. Try another one.")
    else:
        st.subheader("Sign in")
        with st.form("login"):
            username = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            go = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if go:
            found = next((u for u in users if u["username"].casefold() == username.strip().casefold()), None)
            if found and check_password_hash(found["password_hash"], pw):
                sign_in(found); st.rerun()
            else:
                st.error("Incorrect username or password.")


def period_range(period, chosen):
    if period == "Monthly":
        start = chosen.replace(day=1)
        nxt = date(start.year + (start.month == 12), 1 if start.month == 12 else start.month + 1, 1)
        return start, nxt - timedelta(days=1)
    start = chosen - timedelta(days=chosen.weekday())
    return start, start + timedelta(days=6)


def get_period_data(period, chosen):
    start, end = period_range(period, chosen)
    all_rows = rows("waste", "wasted_at")
    selected = [r for r in all_rows if start.isoformat() <= r["wasted_at"][:10] <= end.isoformat()]
    return start, end, selected


def add_waste():
    st.subheader("Record stock wastage")
    catalogue = rows("products")
    with st.form("waste_form", clear_on_submit=True):
        staff = st.text_input("Staff member name")
        category = st.selectbox("Stock category", CATEGORIES)
        options = sorted({p["name"] for p in catalogue if p["category"] == category})
        product_choice = st.selectbox("Product", ["Type a product…"] + options)
        product = st.text_input("Product name (if not in list)") if product_choice == "Type a product…" else product_choice
        c1, c2 = st.columns(2)
        amount = c1.number_input("Amount", min_value=0.0, step=1.0, format="%.3f")
        unit = c2.selectbox("Unit", UNITS + ["other"])
        custom_unit = st.text_input("Specify unit") if unit == "other" else ""
        notes = st.text_area("Notes (optional)")
        save = st.form_submit_button("Save wastage", type="primary", use_container_width=True)
    if save:
        final_unit = custom_unit.strip() if unit == "other" else unit
        if not staff.strip() or not product.strip() or amount <= 0 or not final_unit:
            st.error("Complete all required fields and enter an amount greater than zero.")
        else:
            now = datetime.now().astimezone().isoformat(timespec="minutes")
            sb.table("waste").insert({"staff_name": staff.strip(), "category": category, "product": product.strip(), "amount": float(amount), "unit": final_unit, "notes": notes.strip(), "wasted_at": now, "recorded_by": st.session_state.user["username"]}).execute()
            if not any(p["category"] == category and p["name"].casefold() == product.strip().casefold() for p in catalogue):
                sb.table("products").insert({"category": category, "name": product.strip()}).execute()
            st.success("Wastage saved.")


def dashboard():
    st.subheader("Wastage dashboard")
    c1, c2 = st.columns(2)
    period = c1.selectbox("Report period", ["Weekly", "Monthly"])
    chosen = c2.date_input("Choose a date in the period", value=date.today())
    start, end, data = get_period_data(period, chosen)
    st.caption(f"Showing {start:%d %b %Y} – {end:%d %b %Y}")
    if not data:
        st.info("No wastage recorded in this period yet.")
        return
    df = pd.DataFrame(data)
    a, b, c, d = st.columns(4)
    a.metric("Waste entries", len(df))
    b.metric("People", df.staff_name.nunique())
    c.metric("Categories", df.category.nunique())
    d.metric("Products", df.product.nunique())
    st.markdown("#### Waste by category")
    for cat, group in df.groupby("category", sort=True):
        with st.expander(f"{cat} — {len(group)} entries", expanded=True):
            totals = group.groupby("unit").amount.sum()
            st.write("Total: " + ", ".join(f"{fmt(v)} {u}" for u, v in totals.items()))
            st.dataframe(group.groupby(["product", "unit"], as_index=False).amount.sum(), use_container_width=True, hide_index=True)
            st.caption("Staff breakdown")
            st.dataframe(group.groupby(["staff_name", "product", "unit"], as_index=False).amount.sum(), use_container_width=True, hide_index=True)
    st.markdown("#### Highest wastage products")
    product_rank = df.groupby(["product", "unit"], as_index=False).amount.sum().sort_values("amount", ascending=False).head(10)
    st.dataframe(product_rank, use_container_width=True, hide_index=True)
    st.markdown("#### Highest wastage by staff")
    staff_rank = df.groupby(["staff_name", "unit"], as_index=False).amount.sum().sort_values("amount", ascending=False)
    st.dataframe(staff_rank, use_container_width=True, hide_index=True)
    st.markdown("#### Individual entries")
    show = df[["wasted_at", "staff_name", "category", "product", "amount", "unit", "notes"]].sort_values("wasted_at", ascending=False)
    st.dataframe(show, use_container_width=True, hide_index=True)
    if st.session_state.user["role"] == "admin":
        with st.expander("Delete an entry"):
            choices = {f"#{r['id']} · {r['wasted_at'][:16]} · {r['product']} · {r['staff_name']}": r["id"] for r in data}
            label = st.selectbox("Select entry", list(choices))
            if st.button("Delete selected entry", type="secondary"):
                sb.table("waste").delete().eq("id", choices[label]).execute(); st.rerun()
    st.download_button("⬇️ Export this period to Excel", make_excel(data, start, end, period), file_name=f"stock_wastage_{period.lower()}_{start}_{end}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def make_excel(data, start, end, period):
    wb = Workbook(); log = wb.active; log.title = "Waste Log"
    log.append(["Date/time", "Staff member", "Category", "Product", "Amount", "Unit", "Notes", "Recorded by"])
    for r in data:
        log.append([r["wasted_at"], r["staff_name"], r["category"], r["product"], r["amount"], r["unit"], r.get("notes", ""), r.get("recorded_by", "")])
    cat = wb.create_sheet("Category Summary"); cat.append(["Category", "Product", "Total amount", "Unit"])
    sums = defaultdict(float)
    for r in data: sums[(r["category"], r["product"], r["unit"])] += float(r["amount"])
    for (category, product, unit), value in sorted(sums.items()): cat.append([category, product, value, unit])
    people = wb.create_sheet("People Summary"); people.append(["Staff member", "Category", "Product", "Total amount", "Unit"])
    sums = defaultdict(float)
    for r in data: sums[(r["staff_name"], r["category"], r["product"], r["unit"])] += float(r["amount"])
    for (person, category, product, unit), value in sorted(sums.items()): people.append([person, category, product, value, unit])
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="173F73")
        for col in ws.columns:
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(max(len(str(x.value or "")) for x in col) + 2, 12), 34)
    out = BytesIO(); wb.save(out); return out.getvalue()


def catalogue_page():
    st.subheader("Product catalogue")
    with st.form("new_product"):
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", CATEGORIES)
        name = c2.text_input("Product name")
        add = st.form_submit_button("Add product", type="primary")
    if add and name.strip():
        try: sb.table("products").insert({"category": category, "name": name.strip()}).execute(); st.success("Product added.")
        except Exception: st.warning("That product is already in the catalogue.")
    prods = rows("products")
    for cat in CATEGORIES:
        group = [p for p in prods if p["category"] == cat]
        if group:
            with st.expander(f"{cat} ({len(group)})"):
                for p in group:
                    c1, c2 = st.columns([5, 1]); c1.write(p["name"])
                    if st.session_state.user["role"] == "admin" and c2.button("Remove", key=f"delprod_{p['id']}"):
                        sb.table("products").delete().eq("id", p["id"]).execute(); st.rerun()


def users_page():
    if st.session_state.user["role"] != "admin":
        st.warning("Only the administrator can manage accounts."); return
    st.subheader("User accounts")
    st.caption("You are the administrator. Staff accounts can be added here when you are ready.")
    with st.form("new_user"):
        username = st.text_input("New username")
        password = st.text_input("Temporary password (at least 10 characters)", type="password")
        role = st.selectbox("Access level", ["staff", "admin"])
        add = st.form_submit_button("Create account", type="primary")
    if add:
        if len(username.strip()) < 3 or len(password) < 10: st.error("Enter a username of at least 3 characters and a password of at least 10 characters.")
        else:
            try:
                sb.table("users").insert({"username": username.strip(), "password_hash": generate_password_hash(password), "role": role}).execute(); st.success("Account created.")
            except Exception: st.error("That username is already in use.")
    for u in rows("users"):
        st.write(f"**{u['username']}** — {u['role']}")


if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    auth_screen()
    st.stop()

try:
    ensure_catalogue()
except Exception as exc:
    st.error(f"Could not initialise the product catalogue: {exc}")
    st.stop()

with st.sidebar:
    st.title("📦 Stock Waste Tracker")
    st.caption(f"Signed in as **{st.session_state.user['username']}** ({st.session_state.user['role']})")
    page = st.radio("Navigation", ["Dashboard", "Record wastage", "Product catalogue"] + (["User accounts"] if st.session_state.user["role"] == "admin" else []))
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None; st.rerun()

if page == "Dashboard": dashboard()
elif page == "Record wastage": add_waste()
elif page == "Product catalogue": catalogue_page()
elif page == "User accounts": users_page()
