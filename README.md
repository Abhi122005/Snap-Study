# 📚 Snap & Study

An AI study buddy you can chat with. Snap a photo of a problem, diagram or page of notes (or just type your doubt) and get a plain-language explanation, the key concepts and step-by-step working. When you're done, one button emails your revision notes to your inbox.

Built with **Streamlit**, **Google Gemini** (chat + vision) and **Gmail SMTP** (free, no third-party service).

## Features
- Onboarding once: name, study level (school / college) and email address
- Chat with text or photo input in a single box
- Streaming replies: answers appear word by word
- Structured explanations: Topic, Plain-language explanation, Key concepts, Steps, Quick check
- Explanations are pitched to the student's chosen study level
- System prompt keeps the AI on studying only, and asks for a clearer photo instead of guessing when an image is unreadable or not study material
- Quick-action buttons under the chat: "Explain simpler", "3 practice questions" and "Quiz me"
- "Send to Email" button: Gemini writes revision notes for the whole conversation and Gmail delivers them as a styled HTML email (with a plain-text fallback)
- Safeguards: failed AI answers are never emailed, and sending is capped (3 emails per session, 50 per day across the app) so the sender Gmail account can't be abused



## Project structure
```
snapstudy/
├── app.py                       # the Streamlit app
├── email_template.py            # builds the HTML / plain-text email
├── prompts.py                   # the AI's personality, prompts and quick actions
├── docs/                        # README screenshots
├── requirements.txt
├── .gitignore
└── .streamlit/
    └── secrets.toml.example     # template for your keys
```

## Run locally
1. Clone the repo and create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate        # Windows PowerShell: .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com).
3. Set up the sending Gmail account: turn on 2-Step Verification, then create an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in `GEMINI_API_KEY`, `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` (the 16-character App Password, never your real password).
5. Start the app:
   ```
   streamlit run app.py
   ```
   It opens at http://localhost:8501.

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub (never commit `.streamlit/secrets.toml`).
2. On [share.streamlit.io](https://share.streamlit.io) choose the repo, branch and `app.py`.
3. Paste your secrets into Settings → Secrets and deploy.

## Live app
<your-streamlit-app-url>