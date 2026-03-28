import streamlit as st
import json
from snowflake.snowpark.context import get_active_session
from database import get_all_bookings, delete_booking, update_booking_status


def init_chat_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hi! I'm SkyBot ✈\nI can help you manage flight bookings — ask me to delete, update status, or get info about any booking!"}
        ]
    if "pending_response" not in st.session_state:
        st.session_state.pending_response = False


def build_prompt(user_message: str) -> str:
    bk     = get_all_bookings()
    conf_n = sum(1 for b in bk if b["status"] == "confirmed")
    pend_n = sum(1 for b in bk if b["status"] == "pending")
    canc_n = sum(1 for b in bk if b["status"] == "cancelled")
    rev_n  = sum(float(b["price"]) for b in bk if b["status"] != "cancelled")
    blist  = "\n".join([
        f"- [{b['ref']}] {b['name']} | {b['flight']} ({b['airline']}) | {b['from']}→{b['to']} | {b['date']} | {b['cls']} | ₱{float(b['price']):,} | {b['status']}"
        for b in bk
    ])

    # Build conversation history as text
    history = ""
    for m in st.session_state.chat_history[-6:]:  # last 6 messages for context
        role = "User" if m["role"] == "user" else "Assistant"
        history += f"{role}: {m['content']}\n"

    return f"""You are SkyBot, a flight booking assistant for SkyBook. You CAN perform actions on bookings.

Current booking data:
Total: {len(bk)} | Confirmed: {conf_n} | Pending: {pend_n} | Cancelled: {canc_n} | Revenue: ₱{rev_n:,}

Bookings:
{blist}

You have the ability to...:
1. DELETE a booking when the user asks to delete/remove a booking
2. UPDATE STATUS of a booking (confirmed, pending, cancelled)
3. ANSWER questions about bookings

When the user asks to perform an action, respond ONLY with a JSON block in this exact format:

For delete:
{{"action": "delete", "ref": "SB-XXXXX", "message": "Booking SB-XXXXX for [name] has been deleted."}}

For status update:
{{"action": "update_status", "ref": "SB-XXXXX", "status": "confirmed", "message": "Booking SB-XXXXX for [name] updated to confirmed."}}

For questions (no action), respond normally in plain text without JSON.
Match passenger names case-insensitively. If booking not found, say so in plain text.

Conversation so far:
{history}
User: {user_message}
Assistant:"""


def apply_action(action_data: dict) -> str:
    action = action_data.get("action")
    ref    = action_data.get("ref", "").upper()

    if action == "delete":
        delete_booking(ref=ref)
        return action_data.get("message", f"Booking {ref} deleted.")
    elif action == "update_status":
        new_status = action_data.get("status", "").lower()
        update_booking_status(ref, new_status)
        return action_data.get("message", f"Booking {ref} updated to {new_status}.")
    return action_data.get("message", "Action completed.")


def fetch_bot_reply(user_message: str) -> str:
    try:
        session = get_active_session()
        prompt  = build_prompt(user_message)

        # Escape single quotes for SQL
        prompt_escaped = prompt.replace("'", "\\'")

        result = session.sql(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'claude-3-5-sonnet',
                '{prompt_escaped}'
            ) AS reply
        """).collect()

        reply = result[0]["REPLY"].strip()

        # Check if reply is a JSON action
        if reply.startswith("{") and "action" in reply:
            try:
                action_data = json.loads(reply)
                return apply_action(action_data)
            except json.JSONDecodeError:
                pass

        return reply

    except Exception as e:
        return f"Sorry, I couldn't get a response. ({str(e)[:80]})"


def render_messages(container):
    with container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "assistant":
                st.markdown(f"""
                <div class="chat-msg-bot">
                  <div class="av-bot">✈</div>
                  <div><div class="bubble-bot">{msg['content'].replace(chr(10), '<br>')}</div></div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-msg-user">
                  <div><div class="bubble-user">{msg['content']}</div></div>
                  <div class="av-user">👤</div>
                </div>""", unsafe_allow_html=True)


def render_chatbot():
    st.markdown("""
    <div class="chat-header">
      <div class="chat-avatar">✈</div>
      <div>
        <div class="chat-bot-name">SkyBot Assistant</div>
        <div class="chat-online"><span class="dot-green">●</span> Online · Snowflake Cortex</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    chat_container = st.container(height=520)
    render_messages(chat_container)

    user_input = st.chat_input("e.g. Delete Jose Reyes booking / Mark Ana as confirmed…")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.pending_response = True
        st.rerun()

    if st.session_state.pending_response:
        st.session_state.pending_response = False
        with chat_container:
            st.markdown("""
            <div class="chat-msg-bot">
              <div class="av-bot">✈</div>
              <div><div class="bubble-bot">⏳ Thinking…</div></div>
            </div>""", unsafe_allow_html=True)

        # Get last user message to pass to Cortex
        last_user_msg = next(
            (m["content"] for m in reversed(st.session_state.chat_history) if m["role"] == "user"),
            ""
        )
        reply = fetch_bot_reply(last_user_msg)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()
