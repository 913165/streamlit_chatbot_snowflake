# ✈ SkyBook — Flight Booking System
### Step-by-Step Demo Walkthrough

---

## 🗂 File Creation Order

Build the app in this exact order — each step depends on the previous one.

```
Step 1 → styles.py         (CSS theme — no dependencies)
Step 2 → database.py       (data layer — no dependencies)
Step 3 → booking_list.py   (UI list — depends on database.py)
Step 4 → chatbot.py        (AI chat — depends on database.py)
Step 5 → app.py            (entry point — ties everything together)
```

---

## 📋 Step 1 — `styles.py`
**Purpose:** Dark navy theme CSS shared across the entire app.

**What to show:**
- This is the design foundation — everything visual comes from here
- Single function `load_css()` injected into Streamlit via `st.markdown()`
- Covers navbar, stat cards, table rows, badges, chat bubbles

**Key highlight:**
```python
def load_css():
    st.markdown("""<style> ... </style>""", unsafe_allow_html=True)
```

**Dependencies:** None — start here.

---

## 📋 Step 2 — `database.py`
**Purpose:** All data access via Snowpark — no external DB connection needed.

**What to show:**
- Uses `get_active_session()` — Snowflake handles auth automatically
- Fully qualified table names: `SKYBOOK_DB.BOOKING.PASSENGERS`
- Four tables mapped to Python functions

**Table structure:**
```
AIRLINES    → id, name
PASSENGERS  → id, name, email, phone
FLIGHTS     → id, airline_id, flight_no, origin, destination, travel_date, class
BOOKINGS    → id, ref, passenger_id, flight_id, price, status
```

**Functions exposed:**
```python
get_all_bookings()         # JOIN across all 4 tables
get_airlines()             # dropdown data
add_booking(...)           # INSERT
update_booking(...)        # UPDATE
update_booking_status()    # status-only UPDATE
delete_booking()           # DELETE by id or ref
```

**Key highlight — Snowpark query:**
```python
def get_session():
    return get_active_session()

session.sql("SELECT ... FROM SKYBOOK_DB.BOOKING.BOOKINGS").to_pandas()
```

**Dependencies:** Snowflake session only.

---

## 📋 Step 3 — `booking_list.py`
**Purpose:** Left panel — stats, search, table, add/edit form.

**What to show:**
- Calls `get_all_bookings()` from `database.py` on every render
- Stats bar auto-calculates from live data
- Table built with `st.columns()` — buttons inline with each row
- Edit/Delete buttons are top-level columns (not nested) to avoid vertical stacking

**Key functions:**
```python
render_stats(bookings)   # stat cards — total, confirmed, pending, cancelled, revenue
render_form(bookings)    # add/edit modal form
render_table(filtered)   # column-based table with ✏ 🗑 buttons
render_booking_list()    # main entry — calls all above
```

**Key highlight — inline buttons:**
```python
c0,c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([1.2,1.8,1.4,1.8,1.2,1.0,1.2,0.7,0.7])
# c7 = Edit button (blue), c8 = Delete button (red)
```

**Dependencies:** `database.py`, `styles.py`

---

## 📋 Step 4 — `chatbot.py`
**Purpose:** Right panel — SkyBot AI assistant powered by Snowflake Cortex.

**What to show:**
- No external API key — Cortex runs **inside Snowflake**
- Bot can answer questions AND perform real actions (delete, update status)
- Two-step rerun pattern: show user message immediately, then fetch reply

**How Cortex is called:**
```python
session.sql(f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'claude-3-5-sonnet',
        '{prompt}'
    ) AS reply
""").collect()
```

**Action detection — bot returns JSON for mutations:**
```json
{"action": "delete", "ref": "SB-10022", "message": "Booking deleted."}
{"action": "update_status", "ref": "SB-10023", "status": "confirmed", "message": "Updated."}
```

**Two-step message display:**
```python
# Step 1 — show user message immediately
st.session_state.chat_history.append({"role": "user", "content": user_input})
st.session_state.pending_response = True
st.rerun()

# Step 2 — on next run, fetch and show bot reply
if st.session_state.pending_response:
    reply = fetch_bot_reply(user_message)
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.rerun()
```

**Dependencies:** `database.py`, Snowflake Cortex

---

## 📋 Step 5 — `app.py` (Entry Point)
**Purpose:** Ties all modules together — layout, session, navbar.

**What to show:**
- Thin file — only 35 lines
- `get_active_session()` handles all Snowflake auth
- Two-column layout: booking list (left) + chatbot (right)
- No API keys, no secrets, no external connections

```python
session = get_active_session()   # ← entire auth in one line

left_col, right_col = st.columns([2.8, 1], gap="small")

with left_col:
    render_booking_list()

with right_col:
    render_chatbot()
```

**Dependencies:** All other files.

---

## 🏗 Full Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Snowflake Platform                   │
│                                                         │
│  ┌──────────────┐          ┌──────────────────────────┐ │
│  │  Streamlit   │          │     Snowflake Cortex     │ │
│  │   (UI App)   │◄────────►│  claude-3-5-sonnet LLM  │ │
│  └──────┬───────┘          └──────────────────────────┘ │
│         │                                               │
│         │  Snowpark session.sql()                       │
│         ▼                                               │
│  ┌──────────────────────────────────────┐               │
│  │         SKYBOOK_DB.BOOKING           │               │
│  │                                      │               │
│  │  AIRLINES   PASSENGERS   FLIGHTS     │               │
│  │       └──────────┴────► BOOKINGS     │               │
│  └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Demo Script (Suggested Order)

| Step | Action | What to highlight |
|------|--------|-------------------|
| 1 | Open app | Dark navy theme, split layout |
| 2 | Show stats bar | Live count from Snowflake |
| 3 | Search a passenger | Real-time filter |
| 4 | Click ✏ Edit | Form pre-filled from DB |
| 5 | Click 🗑 Delete | Row removed, stats update |
| 6 | Click + Add | Insert into Snowflake |
| 7 | Ask SkyBot "who has pending bookings?" | Cortex reads live data |
| 8 | Say "Delete Jose Reyes booking" | Cortex performs DB action |
| 9 | Say "Mark Ana as confirmed" | Status updates instantly |

---

## 🚀 Deployment

1. Go to **Snowflake → Streamlit → + Streamlit App**
2. Upload files in this order:
   - `styles.py`
   - `database.py`
   - `booking_list.py`
   - `chatbot.py`
   - `app.py` ← set as **Main file**
3. No secrets or API keys needed
4. Click **Run**

---

## 📦 Prerequisites

- Snowflake account with **Cortex enabled**
- Database `SKYBOOK_DB` with schema `BOOKING` and 4 tables populated
- Role with `USAGE` on `SNOWFLAKE.CORTEX`
