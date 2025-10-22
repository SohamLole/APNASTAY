import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import io
import hashlib

DB_PATH = "pg_accounts.db"

# --------------------------- AUTHENTICATION ---------------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_auth():
    conn = get_conn()
    cur = conn.cursor()
    
    # Create users table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- admin | tenant
            tenant_id INTEGER,
            FOREIGN KEY(tenant_id) REFERENCES tenants(id)
        );
        """
    )
    
    # Create default admin user if not exists
    admin_hash = hash_password("admin123")
    try:
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", admin_hash, "admin")
        )
    except:
        pass
    
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    
    password_hash = hash_password(password)
    cur.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    )
    
    user = cur.fetchone()
    conn.close()
    
    return user

# --------------------------- DB HELPERS ---------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            rent REAL NOT NULL,
            deposit REAL DEFAULT 0,
            status TEXT DEFAULT 'vacant' -- vacant | occupied | maintenance
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            room_id INTEGER,
            join_date TEXT,
            leave_date TEXT,
            deposit_paid REAL DEFAULT 0,
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            kind TEXT NOT NULL, -- rent | deposit | other
            notes TEXT,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            FOREIGN KEY(tenant_id) REFERENCES tenants(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            vendor TEXT,
            notes TEXT
        );
        """
    )

    conn.commit()
    conn.close()

# --------------------------- UTILS ---------------------------

def df_from_query(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def exec_query(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def money(x):
    try:
        return f"₹{float(x):,.0f}"
    except Exception:
        return x

# --------------------------- RENT LOGIC ---------------------------

def monthly_rent_due(tenant_id: int) -> float:
    """Return the configured monthly rent for the tenant's assigned room."""
    row = df_from_query(
        """
        SELECT r.rent FROM tenants t
        JOIN rooms r ON r.id = t.room_id
        WHERE t.id = ?
        """,
        (tenant_id,),
    )
    if row.empty:
        return 0.0
    return float(row.iloc[0]["rent"]) or 0.0

def tenant_name(tenant_id: int) -> str:
    df = df_from_query("SELECT name FROM tenants WHERE id = ?", (tenant_id,))
    return df.iloc[0]["name"] if not df.empty else "Unknown"

def arrears_for_month(year: int, month: int) -> pd.DataFrame:
    # List active tenants in the month (joined before or in month, not left before month end)
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    active = df_from_query(
        """
        SELECT t.id AS tenant_id, t.name, r.name AS room_name, r.rent
        FROM tenants t
        LEFT JOIN rooms r ON r.id = t.room_id
        WHERE (t.join_date IS NULL OR date(t.join_date) < date(?))
          AND (t.leave_date IS NULL OR date(t.leave_date) >= date(?))
        ORDER BY t.name
        """,
        (month_end.isoformat(), month_start.isoformat()),
    )

    pays = df_from_query(
        """
        SELECT tenant_id, COALESCE(SUM(amount),0) AS paid
        FROM payments
        WHERE year = ? AND month = ? AND kind = 'rent'
        GROUP BY tenant_id
        """,
        (year, month),
    )

    merged = active.merge(pays, how="left", on="tenant_id")
    merged["paid"] = merged["paid"].fillna(0.0)
    merged["due"] = merged["rent"].fillna(0.0) - merged["paid"]
    return merged

# --------------------------- UI ---------------------------

def login_page():
    st.title("🏠 ApnaStay PG Accounting")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Admin Login")
        with st.form("admin_login"):
            admin_username = st.text_input("Admin Username")
            admin_password = st.text_input("Password", type="password")
            admin_submit = st.form_submit_button("Login as Admin")
            
            if admin_submit:
                user = authenticate_user(admin_username, admin_password)
                if user and user["role"] == "admin":
                    st.session_state.user = user
                    st.session_state.role = "admin"
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    st.error("Invalid admin credentials")
    
    with col2:
        st.subheader("Tenant Login")
        with st.form("tenant_login"):
            tenant_username = st.text_input("Tenant Username")
            tenant_password = st.text_input("Password", type="password")
            tenant_submit = st.form_submit_button("Login as Tenant")
            
            if tenant_submit:
                user = authenticate_user(tenant_username, tenant_password)
                if user and user["role"] == "tenant":
                    st.session_state.user = user
                    st.session_state.role = "tenant"
                    st.success("Tenant login successful!")
                    st.rerun()
                else:
                    st.error("Invalid tenant credentials")

def sidebar_branding():
    st.sidebar.title("🏠 ApnaStay PG")
    if "user" in st.session_state:
        st.sidebar.write(f"Welcome, **{st.session_state.user['username']}**")
        st.sidebar.write(f"Role: **{st.session_state.role.title()}**")
    
    st.sidebar.markdown("---")

def page_dashboard():
    st.subheader("📊 Dashboard")
    today = date.today()
    year = st.selectbox("Year", options=list(range(today.year - 3, today.year + 2)), index=3)
    month = st.selectbox("Month", options=list(range(1, 13)), index=today.month - 1)

    # Occupancy
    occ = df_from_query(
        """
        SELECT 
            SUM(CASE WHEN status='occupied' THEN 1 ELSE 0 END) AS occupied,
            SUM(CASE WHEN status='vacant' THEN 1 ELSE 0 END) AS vacant,
            COUNT(*) AS total
        FROM rooms
        """
    )
    if not occ.empty:
        o = int(occ.loc[0, "occupied"]) or 0
        v = int(occ.loc[0, "vacant"]) or 0
        t = int(occ.loc[0, "total"]) or 0
        rate = (o / t * 100) if t else 0
    else:
        o = v = t = rate = 0

    # Revenue & dues
    rent_collected = df_from_query(
        "SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE year=? AND month=? AND kind='rent'",
        (year, month),
    )["s"].iloc[0]

    # Expected rent = sum of rent of active tenants
    arr = arrears_for_month(year, month)
    expected_rent = arr["rent"].sum()
    total_due = arr["due"].clip(lower=0).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rooms occupied", o)
    c2.metric("Vacant rooms", v)
    c3.metric("Occupancy rate", f"{rate:.0f}%")
    c4.metric("Rent collected", money(rent_collected))

    st.markdown("---")
    st.markdown("#### 🧾 Monthly Arrears")
    st.dataframe(arr[["name", "room_name", "rent", "paid", "due"]].rename(columns={"name": "Tenant", "room_name": "Room", "rent": "Rent", "paid": "Paid", "due": "Due"}), use_container_width=True)

    st.download_button(
        "Download arrears (CSV)",
        data=arr.to_csv(index=False).encode("utf-8"),
        file_name=f"arrears_{year}_{month}.csv",
        mime="text/csv",
    )

def page_rooms():
    st.subheader("🛏️ Rooms")
    with st.expander("Add room", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Room name/number")
        with col2:
            rent = st.number_input("Monthly rent", min_value=0.0, step=500.0)
        with col3:
            deposit = st.number_input("Deposit", min_value=0.0, step=500.0)
        status = st.selectbox("Status", ["vacant", "occupied", "maintenance"])
        if st.button("➕ Save room"):
            if name:
                try:
                    exec_query("INSERT INTO rooms(name, rent, deposit, status) VALUES (?,?,?,?)", (name, rent, deposit, status))
                    st.success("Room added")
                except sqlite3.IntegrityError:
                    st.error("Room name must be unique")
            else:
                st.warning("Please enter a room name")

    df = df_from_query("SELECT * FROM rooms ORDER BY name")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        rid = st.number_input("Room ID to delete (careful)", min_value=0, step=1)
        if st.button("🗑️ Delete room") and rid:
            exec_query("DELETE FROM rooms WHERE id = ?", (rid,))
            st.info("Deleted. Refresh to see changes.")
    else:
        st.info("No rooms yet. Add one above.")

def page_tenants():
    st.subheader("👤 Tenants")
    with st.expander("Add tenant", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full name")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            join_date = st.date_input("Join date", value=date.today())
        with c2:
            rooms = df_from_query("SELECT id, name FROM rooms ORDER BY name")
            room_map = {f"{r['name']} (#{r['id']})": r["id"] for _, r in rooms.iterrows()} if not rooms.empty else {}
            room_choice = st.selectbox("Assign room", ["-- none --"] + list(room_map.keys()))
            leave_date = st.date_input("Leave date (optional)", value=None, format="YYYY-MM-DD")
            deposit_paid = st.number_input("Deposit paid", min_value=0.0, step=500.0)
        if st.button("➕ Save tenant"):
            room_id = None if room_choice == "-- none --" else room_map[room_choice]
            tenant_id = exec_query(
                """
                INSERT INTO tenants(name, phone, email, room_id, join_date, leave_date, deposit_paid)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    name,
                    phone,
                    email,
                    room_id,
                    join_date.isoformat() if join_date else None,
                    leave_date.isoformat() if leave_date else None,
                    deposit_paid,
                ),
            )
            if room_id:
                exec_query("UPDATE rooms SET status='occupied' WHERE id=?", (room_id,))
            
            # Create user account for tenant
            if tenant_id:
                username = name.lower().replace(" ", "_")
                password_hash = hash_password("password123")
                exec_query(
                    "INSERT INTO users (username, password_hash, role, tenant_id) VALUES (?, ?, ?, ?)",
                    (username, password_hash, "tenant", tenant_id)
                )
            
            st.success("Tenant added")

    df = df_from_query(
        """
        SELECT t.*, r.name AS room_name FROM tenants t
        LEFT JOIN rooms r ON r.id = t.room_id
        ORDER BY t.name
        """
    )
    if not df.empty:
        show = df[["id", "name", "phone", "email", "room_name", "join_date", "leave_date", "deposit_paid"]]
        st.dataframe(show.rename(columns={"room_name": "Room"}), use_container_width=True)
        tid = st.number_input("Tenant ID to delete (careful)", min_value=0, step=1)
        if st.button("🗑️ Delete tenant") and tid:
            exec_query("DELETE FROM tenants WHERE id = ?", (tid,))
            exec_query("DELETE FROM users WHERE tenant_id = ?", (tid,))
            st.info("Deleted. Refresh to see changes.")
    else:
        st.info("No tenants yet. Add one above.")

def page_payments():
    st.subheader("💸 Payments")
    with st.expander("Add payment", expanded=False):
        tenants = df_from_query("SELECT id, name FROM tenants ORDER BY name")
        tmap = {f"{r['name']} (#{r['id']})": r["id"] for _, r in tenants.iterrows()} if not tenants.empty else {}
        tchoice = st.selectbox("Tenant", list(tmap.keys()) if tmap else ["-- no tenants --"])
        pay_date = st.date_input("Payment date", value=date.today())
        amount = st.number_input("Amount", min_value=0.0, step=500.0)
        kind = st.selectbox("Type", ["rent", "deposit", "other"])
        notes = st.text_input("Notes")
        # Default to selected month/year
        today = date.today()
        col1, col2 = st.columns(2)
        with col1:
            month = st.number_input("For month (1-12)", min_value=1, max_value=12, value=today.month)
        with col2:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=today.year)

        if st.button("➕ Save payment"):
            if not tmap:
                st.warning("Add a tenant first")
            else:
                exec_query(
                    """
                    INSERT INTO payments(tenant_id, date, amount, kind, notes, month, year)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (tmap[tchoice], pay_date.isoformat(), amount, kind, notes, int(month), int(year)),
                )
                st.success("Payment recorded")

    df = df_from_query(
        """
        SELECT p.id, t.name AS tenant, p.date, p.amount, p.kind, p.notes, p.month, p.year
        FROM payments p
        JOIN tenants t ON t.id = p.tenant_id
        ORDER BY p.date DESC, p.id DESC
        """
    )
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download payments (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="payments.csv",
            mime="text/csv",
        )
        pid = st.number_input("Payment ID to delete (careful)", min_value=0, step=1)
        if st.button("🗑️ Delete payment") and pid:
            exec_query("DELETE FROM payments WHERE id = ?", (pid,))
            st.info("Deleted. Refresh to see changes.")
    else:
        st.info("No payments yet.")

def page_expenses():
    st.subheader("🧾 Expenses")
    with st.expander("Add expense", expanded=False):
        e_date = st.date_input("Date", value=date.today())
        amount = st.number_input("Amount", min_value=0.0, step=100.0)
        category = st.text_input("Category (e.g., utilities, repair, supplies)")
        vendor = st.text_input("Vendor (optional)")
        notes = st.text_input("Notes")
        if st.button("➕ Save expense"):
            exec_query(
                "INSERT INTO expenses(date, amount, category, vendor, notes) VALUES (?,?,?,?,?)",
                (e_date.isoformat(), amount, category, vendor, notes),
            )
            st.success("Expense saved")

    df = df_from_query("SELECT * FROM expenses ORDER BY date DESC, id DESC")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download expenses (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="expenses.csv",
            mime="text/csv",
        )
        eid = st.number_input("Expense ID to delete (careful)", min_value=0, step=1)
        if st.button("🗑️ Delete expense") and eid:
            exec_query("DELETE FROM expenses WHERE id = ?", (eid,))
            st.info("Deleted. Refresh to see changes.")
    else:
        st.info("No expenses yet.")

def page_reports():
    st.subheader("📈 Reports")
    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        year = st.number_input("Year", min_value=2000, max_value=2100, value=today.year)
    with c2:
        month = st.number_input("Month", min_value=1, max_value=12, value=today.month)

    tabs = st.tabs(["Monthly summary", "Arrears", "Tenant statement"])    

    with tabs[0]:
        # Revenue (payments) vs expenses
        rev = df_from_query(
            "SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE year=? AND month=?",
            (int(year), int(month)),
        )["s"].iloc[0]
        exp = df_from_query(
            "SELECT COALESCE(SUM(amount),0) AS s FROM expenses WHERE strftime('%Y', date)=? AND strftime('%m', date)=?",
            (str(int(year)), f"{int(month):02d}"),
        )["s"].iloc[0]
        st.metric("Total collections (all types)", money(rev))
        st.metric("Total expenses", money(exp))
        st.metric("Net (collections - expenses)", money(rev - exp))

        rent_collected = df_from_query(
            "SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE year=? AND month=? AND kind='rent'",
            (int(year), int(month)),
        )["s"].iloc[0]
        exp_rent = arrears_for_month(int(year), int(month))["rent"].sum()
        st.metric("Rent collected (this month)", money(rent_collected))
        st.metric("Rent expected (active tenants)", money(exp_rent))

    with tabs[1]:
        arr = arrears_for_month(int(year), int(month))
        st.dataframe(arr[["name", "room_name", "rent", "paid", "due"]].rename(columns={"name": "Tenant", "room_name": "Room"}), use_container_width=True)

    with tabs[2]:
        tdf = df_from_query("SELECT id, name FROM tenants ORDER BY name")
        if tdf.empty:
            st.info("No tenants")
        else:
            tmap = {r["name"]: r["id"] for _, r in tdf.iterrows()}
            name = st.selectbox("Tenant", list(tmap.keys()))
            tid = tmap[name]
            # Basic info
            info = df_from_query(
                """
                SELECT t.name, t.phone, t.email, t.join_date, t.leave_date, t.deposit_paid,
                       r.name AS room, r.rent
                FROM tenants t LEFT JOIN rooms r ON r.id = t.room_id
                WHERE t.id = ?
                """,
                (tid,),
            )
            st.write("**Room:**", info.iloc[0]["room"])
            st.write("**Monthly rent:**", money(info.iloc[0]["rent"]))
            st.write("**Joined:**", info.iloc[0]["join_date"])
            st.write("**Left:**", info.iloc[0]["leave_date"])            
            st.write("**Deposit paid:**", money(info.iloc[0]["deposit_paid"]))

            pays = df_from_query(
                "SELECT date, amount, kind, notes, month, year FROM payments WHERE tenant_id=? ORDER BY date DESC",
                (tid,),
            )
            st.markdown("**Payment history**")
            st.dataframe(pays, use_container_width=True)

            # Month summary selector
            col1, col2 = st.columns(2)
            with col1:
                m = st.number_input("Month", 1, 12, value=today.month)
            with col2:
                y = st.number_input("Year", 2000, 2100, value=today.year)
            rent = monthly_rent_due(tid)
            paid = df_from_query(
                "SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE tenant_id=? AND year=? AND month=? AND kind='rent'",
                (tid, int(y), int(m)),
            )["s"].iloc[0]
            st.write(f"**Due for {int(m)}/{int(y)}:**", money(max(rent - paid, 0)))

            # Export statement
            buf = io.StringIO()
            pays.to_csv(buf, index=False)
            st.download_button(
                f"Download payment history - {name} (CSV)",
                data=buf.getvalue().encode("utf-8"),
                file_name=f"{name.replace(' ', '_')}_payments.csv",
                mime="text/csv",
            )

def page_settings():
    st.subheader("⚙️ Settings & Backup")
    st.markdown("**Download database backup**")
    with open(DB_PATH, "rb") as f:
        st.download_button("Download pg_accounts.db", f.read(), file_name="pg_accounts.db")

    st.markdown("---")
    st.markdown("**Restore from backup** (upload a previously downloaded `pg_accounts.db`) ")
    upl = st.file_uploader("Upload DB file", type=["db"]) 
    if upl is not None:
        with open(DB_PATH, "wb") as f:
            f.write(upl.read())
        st.success("Database restored. Please reload the app.")

def tenant_dashboard():
    st.subheader("👤 My Dashboard")
    
    if "user" not in st.session_state:
        st.error("Not logged in")
        return
    
    # Get tenant information
    tenant_info = df_from_query(
        """
        SELECT t.*, r.name as room_name, r.rent 
        FROM tenants t 
        LEFT JOIN rooms r ON t.room_id = r.id 
        WHERE t.id = ?
        """,
        (st.session_state.user["tenant_id"],)
    )
    
    if not tenant_info.empty:
        tenant = tenant_info.iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("My Room", tenant["room_name"])
            st.metric("Monthly Rent", money(tenant["rent"]))
            st.metric("Deposit Paid", money(tenant["deposit_paid"]))
        
        with col2:
            st.write("**Personal Information**")
            st.write(f"**Name:** {tenant['name']}")
            st.write(f"**Phone:** {tenant['phone']}")
            st.write(f"**Email:** {tenant['email']}")
            st.write(f"**Join Date:** {tenant['join_date']}")
        
        # Payment history
        st.markdown("---")
        st.subheader("💰 My Payment History")
        
        payments = df_from_query(
            """
            SELECT date, amount, kind, notes, month, year 
            FROM payments 
            WHERE tenant_id = ? 
            ORDER BY date DESC
            """,
            (st.session_state.user["tenant_id"],)
        )
        
        if not payments.empty:
            st.dataframe(payments, use_container_width=True)
            
            # Current month dues
            today = date.today()
            rent_due = monthly_rent_due(st.session_state.user["tenant_id"])
            paid_this_month = df_from_query(
                "SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE tenant_id=? AND year=? AND month=? AND kind='rent'",
                (st.session_state.user["tenant_id"], today.year, today.month),
            )["s"].iloc[0]
            
            st.metric(f"Due for {today.strftime('%B %Y')}", money(max(rent_due - paid_this_month, 0)))
        else:
            st.info("No payment history found")
    else:
        st.error("Tenant information not found")

# --------------------------- MAIN ---------------------------

def main():
    st.set_page_config(page_title="ApnaStay PG Accounting", page_icon="🏠", layout="wide")
    
    # Initialize database and authentication
    init_db()
    init_auth()
    
    # Check if user is logged in
    if "user" not in st.session_state:
        login_page()
        return
    
    # User is logged in - show main application
    sidebar_branding()
    
    # Navigation based on role
    if st.session_state.role == "admin":
        pages = {
            "Dashboard": page_dashboard,
            "Rooms": page_rooms,
            "Tenants": page_tenants,
            "Payments": page_payments,
            "Expenses": page_expenses,
            "Reports": page_reports,
            "Settings": page_settings,
        }
    else:  # tenant
        pages = {
            "My Dashboard": tenant_dashboard,
            "Payment History": page_payments,
        }
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Page selection
    selected_page = st.sidebar.radio("Navigate", list(pages.keys()))
    
    # Display selected page
    pages[selected_page]()

if __name__ == "__main__":
    main()