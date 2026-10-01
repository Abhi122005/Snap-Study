import re
import smtplib
import threading
from datetime import date
from email.message import EmailMessage

import streamlit as st
from google import genai
from google.genai import types

from email_template import build_email
from prompts import (
    DEFAULT_PHOTO_PROMPT,
    QUICK_ACTIONS,
    SUMMARY_REQUEST_PROMPT,
    SYSTEM_PROMPT_TEMPLATE,
    WELCOME_MESSAGE_TEMPLATE,
)

MODEL_NAME = "gemini-3.5-flash"  # use any Gemini model your key can access
LEVELS = ["School (Class 6-8)", "School (Class 9-12)", "College / University"]
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Safeguards: the app sends from ONE Gmail account, so cap how much it can send.
MAX_EMAILS_PER_SESSION = 3
DAILY_EMAIL_LIMIT = 50  # across all visitors; Gmail's own limit is ~500/day

st.set_page_config(page_title="Snap & Study", page_icon="📚")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"].replace(" ", "")


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


@st.cache_resource
def get_daily_counter():
    # Shared by every visitor of the running app (survives reruns and refreshes).
    return {"day": date.today(), "count": 0, "lock": threading.Lock()}


gemini_client = get_gemini_client()


def daily_limit_reached():
    counter = get_daily_counter()
    with counter["lock"]:
        if counter["day"] != date.today():
            counter["day"], counter["count"] = date.today(), 0
        return counter["count"] >= DAILY_EMAIL_LIMIT


def record_daily_send():
    counter = get_daily_counter()
    with counter["lock"]:
        counter["count"] += 1


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content, error=False, render=True):
    st.session_state.messages.append(
        {"role": role, "kind": kind, "content": content, "error": error}
    )
    if render:
        render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    """Returns (ok, text). ok is False if Gemini failed or returned nothing."""
    try:
        text = st.session_state.chat.send_message(parts).text
        if not text or not text.strip():
            return False, "Sorry, I got an empty answer. Please try again."
        return True, text
    except Exception as error:
        return False, f"Sorry, something went wrong: {error}"


def stream_gemini(parts, result):
    """Yields the answer chunk by chunk (for st.write_stream) and records
    the full text and success flag in `result`."""
    try:
        for chunk in st.session_state.chat.send_message_stream(parts):
            if chunk.text:
                result["text"] += chunk.text
                yield chunk.text
        if not result["text"].strip():
            result["ok"] = False
            result["text"] = "Sorry, I got an empty answer. Please try again."
            yield result["text"]
    except Exception as error:
        result["ok"] = False
        message = f"\n\nSorry, something went wrong: {error}"
        result["text"] += message
        yield message


def send_email(to_address, user_name, summary):
    try:
        message = EmailMessage()
        message["Subject"] = "📚 Your Snap & Study notes"
        message["From"] = GMAIL_ADDRESS
        message["To"] = to_address
        plain_text, html = build_email(user_name, summary)
        message.set_content(plain_text)  # fallback for clients that can't show HTML
        message.add_alternative(html, subtype="html")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(message)
        return True, "sent"
    except Exception as error:
        return False, str(error)


def run_turn(text, photo):
    """One chat turn: show the user's input, ask Gemini, show the reply."""
    parts = []
    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append(DEFAULT_PHOTO_PROMPT)

    result = {"ok": True, "text": ""}
    with st.chat_message("assistant"):
        st.write_stream(stream_gemini(parts, result))  # answer appears word by word
    add_message("assistant", "text", result["text"], error=not result["ok"], render=False)
    st.rerun()  # redraw so the buttons re-check the updated chat state


def handle_send_notes():
    if st.session_state.emails_sent >= MAX_EMAILS_PER_SESSION:
        st.error(f"You've reached the limit of {MAX_EMAILS_PER_SESSION} emails per session.")
        return
    if daily_limit_reached():
        st.error("Today's email limit for this app has been reached. Please try again tomorrow.")
        return

    with st.spinner("Writing your revision notes..."):
        ok, summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
    if not ok:
        st.warning("I couldn't prepare your notes just now, so nothing was sent. Please try again.")
        return

    success, info = send_email(st.session_state.email, st.session_state.name, summary)
    if success:
        st.session_state.emails_sent += 1
        record_daily_send()
        st.success("Sent! Check your inbox 📧 (and your spam folder)")
    else:
        st.error(f"Couldn't send that: {info}")


# Step 1: onboarding
if "onboarded" not in st.session_state:
    st.title("📚 Snap & Study")
    st.caption("Snap it. Understand it. Email yourself the notes.")
    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        level = st.selectbox("Your study level", LEVELS)
        email = st.text_input(
            "Your email address",
            placeholder="you@example.com",
            help="This is where Snap & Study will send your notes.",
        )
        submitted = st.form_submit_button("Let's go 🚀")
    if submitted:
        if not name.strip() or not email.strip():
            st.warning("Please fill in both your name and email address.")
        elif not EMAIL_PATTERN.match(email.strip()):
            st.warning("That email address doesn't look right - please check it.")
        else:
            st.session_state.name = name.strip()
            st.session_state.email = email.strip()
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT_TEMPLATE.format(level=level)
                ),
            )
            st.session_state.messages = []
            st.session_state.emails_sent = 0
            st.session_state.onboarded = True
            st.rerun()
    st.stop()

# Step 2: chat interface
# A "real" answer = an assistant message that isn't the welcome (index 0) or an error.
has_answer = any(
    m["role"] == "assistant" and not m["error"] for m in st.session_state.messages[1:]
)
limit_reached = st.session_state.emails_sent >= MAX_EMAILS_PER_SESSION

header_col, button_col = st.columns([5, 2], vertical_alignment="center")

with header_col:
    st.title("📚 Snap & Study")

with button_col:
    if st.button(
        "📤 Send to Email",
        disabled=(not has_answer) or limit_reached,
        use_container_width=True,
    ):
        handle_send_notes()

st.caption(
    f"Logged in as {st.session_state.name} - notes go to {st.session_state.email} "
    f"· Emails sent: {st.session_state.emails_sent}/{MAX_EMAILS_PER_SESSION}"
)

if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

# Quick-action buttons (enabled once there's something to follow up on)
quick_prompt = None
quick_cols = st.columns(len(QUICK_ACTIONS))
for col, (label, prompt) in zip(quick_cols, QUICK_ACTIONS.items()):
    if col.button(label, use_container_width=True, disabled=not has_answer):
        quick_prompt = prompt

user_input = st.chat_input(
    "Type your doubt, or attach a photo of a problem / notes",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if quick_prompt:
    run_turn(quick_prompt, None)
elif user_input:
    photo = user_input.files[0] if user_input.files else None
    run_turn(user_input.text, photo)