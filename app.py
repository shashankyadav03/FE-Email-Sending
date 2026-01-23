import streamlit as st
import requests
import pandas as pd
from dotenv import load_dotenv
import os

# --------------------------------
# ENV SETUP
# --------------------------------
load_dotenv()

FUNCTION_BASE = os.getenv("FUNCTION_BASE")
FUNCTION_KEY  = os.getenv("FUNCTION_KEY")

CREATE_URL = f"{FUNCTION_BASE}/emails/create?code={FUNCTION_KEY}"
SEND_URL   = f"{FUNCTION_BASE}/emails/send?code={FUNCTION_KEY}"
HEALTH_URL = f"{FUNCTION_BASE}/health?code={FUNCTION_KEY}"

# --------------------------------
# HARDCODED CANDIDATES
# --------------------------------
hardcoded_candidates = [
    {
        "name": "Shash",
        "email": "shashankyadav4858@gmail.com",
        "location_preference": "Delhi",
        "disability": "None",
        "educational_qualification": "Masters",
        "work_experience": "5",
        "summary": "AI Engineer with 5 years of experience in machine learning and data science.",
        "id": "100"
    },
    {
        "name": "Shashwat",
        "email": "shashwat1606@gmail.com",
        "location_preference": "Bangalore",
        "disability": "None",
        "educational_qualification": "Bachelors",
        "work_experience": "5",
        "summary": "Investment banker with 5 years of experience in financial analysis and portfolio management.",
        "id": "200"
    },
    {
        "name": "Vertika",
        "email": "Vertika@atypicaladvantage.in",
        "location_preference": "Mumbai",
        "disability": "None",
        "educational_qualification": "Masters",
        "work_experience": "3",
        "summary": "Recruiter with 3 years of experience in talent acquisition and human resources.",
        "id": "300"
    },
    {
        "name": "Preeti",
        "email": "Preeti@atypicaladvantage.in",
        "location_preference": "Hyderabad",
        "disability": "None",
        "educational_qualification": "Bachelors",
        "work_experience": "4",
        "summary": "Recruiter with 4 years of experience in recruitment and talent management.",
        "id": "400"
    },
    {
        "name": "Talent Onboarding",
        "email": "talentonboarding@atypicaladvantage.in",
        "location_preference": "Chennai",
        "disability": "None",
        "educational_qualification": "Masters",
        "work_experience": "6",
        "summary": "Expert in talent onboarding with 6 years of experience in employee integration and training.",
        "id": "500"
    },
    {
        "name": "Juhi",
        "email": "juhi@atypicaladvantage.in",
        "location_preference": "Pune",
        "disability": "None",
        "educational_qualification": "Bachelors",
        "work_experience": "2",
        "summary": "Top recruiter with 3 years of experience in sourcing and hiring top talent.",
        "id": "600"
    }
]

# --------------------------------
# SESSION STATE
# --------------------------------
if "candidates" not in st.session_state:
    st.session_state.candidates = []

if "selected" not in st.session_state:
    st.session_state.selected = []

if "generated_emails" not in st.session_state:
    st.session_state.generated_emails = []

if "job_id" not in st.session_state:
    st.session_state.job_id = None

# --------------------------------
# UI
# --------------------------------
st.set_page_config("AI Recruiter", layout="wide")
st.title("🤖 AI Candidate Outreach (Service 1 Tester)")

# --------------------------------
# HEALTH CHECK
# --------------------------------
with st.sidebar:
    st.subheader("API")
    if st.button("Check API Health"):
        try:
            r = requests.get(HEALTH_URL, timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(str(e))

# --------------------------------
# JOB DESCRIPTION
# --------------------------------
job_desc = st.text_area(
    "Job Description",
    "We are hiring a recruiter with 3–5 years experience."
)

# --------------------------------
# LOAD CANDIDATES
# --------------------------------
if st.button("🔍 Search Candidates"):
    st.session_state.candidates = hardcoded_candidates

if st.session_state.candidates:
    df = pd.DataFrame(st.session_state.candidates)

    st.subheader("Candidate List")

    st.data_editor(
        df,
        width=1200,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True),
            "name": "Name",
            "email": "Email",
            "location_preference": "Location",
            "educational_qualification": "Education",
            "work_experience": "Experience",
            "summary": "Summary"
        }
    )

    st.session_state.selected = st.multiselect(
        "Select candidates to email",
        options=df["email"].tolist()
    )

    st.info(f"Selected {len(st.session_state.selected)} candidates")

# --------------------------------
# GENERATE EMAILS
# --------------------------------
if st.button("🚀 Generate AI Emails"):
    if not st.session_state.selected:
        st.error("Select at least one candidate")
    else:
        selected_candidates = [
            c for c in st.session_state.candidates
            if c["email"] in st.session_state.selected
        ]

        payload = {
            "job": {
                "title": "Recruiter Role",
                "description": job_desc,
                "company_name": "Atypical Advantage",
                "location": "India",
                "contact_email": "jobs@atypicaladvantage.in"
            },
            "candidates": selected_candidates
        }

        with st.spinner("Generating emails..."):
            try:
                r = requests.post(CREATE_URL, json=payload, timeout=60)
                data = r.json()
            except Exception as e:
                st.error(str(e))
                data = {}

            if data.get("success"):
                st.session_state.generated_emails = data.get("emails", [])
                st.session_state.job_id = data.get("job_id")
                st.success(f"Generated {len(st.session_state.generated_emails)} emails")
            else:
                st.error(data.get("error", "Failed to generate emails"))

# --------------------------------
# PREVIEW & EDIT EMAILS
# --------------------------------
if st.session_state.generated_emails:
    st.subheader("✏️ Review & Edit Emails")

    for i, email in enumerate(st.session_state.generated_emails):
        with st.expander(email["email"]):
            email["subject"] = st.text_input(
                "Subject", email["subject"], key=f"subject_{i}"
            )
            email["body"] = st.text_area(
                "Body", email["body"], height=220, key=f"body_{i}"
            )

# --------------------------------
# SEND EMAILS
# --------------------------------
if st.button("✅ Send Emails"):
    if not st.session_state.generated_emails:
        st.error("No emails to send")
    else:
        payload = {
            "job_id": st.session_state.job_id,
            "emails": st.session_state.generated_emails
        }

        with st.spinner("Sending emails..."):
            try:
                r = requests.post(SEND_URL, json=payload, timeout=60)
                data = r.json()
            except Exception as e:
                st.error(str(e))
                data = {}

        if data.get("success"):
            # Safe count handling (NO KeyError)
            if "emails_sent" in data:
                sent_count = data["emails_sent"]
            elif "details" in data and isinstance(data["details"], list):
                sent_count = len(data["details"])
            else:
                sent_count = len(st.session_state.generated_emails)

            st.success(f"Sent {sent_count} emails")

            if data.get("details"):
                st.subheader("📬 Delivery Status")
                st.table(pd.DataFrame(data["details"]))

            st.session_state.generated_emails = []
        else:
            st.error(data.get("error", "Failed to send emails"))