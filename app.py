import streamlit as st
import requests
import pandas as pd

# --------------------------------
# Azure Function Config
# --------------------------------
# ...existing code...
from dotenv import load_dotenv
import os
load_dotenv()

# --------------------------------
# CONFIG – change only these
# --------------------------------
FUNCTION_BASE = os.getenv("FUNCTION_BASE")
FUNCTION_KEY  = os.getenv("FUNCTION_KEY")   # set in .env

CREATE_URL = f"{FUNCTION_BASE}/emails/create?code={FUNCTION_KEY}"
SEND_URL   = f"{FUNCTION_BASE}/emails/send?code={FUNCTION_KEY}"
HEALTH_URL = f"{FUNCTION_BASE}/health?code={FUNCTION_KEY}"
# ...existing code...

# --------------------------------
# Hardcoded Candidates
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
        "summary": "Recuiter with 3 years of experience in talent acquisition and human resources.",
        "id": "300"
    },
    {
        "name": "Preeti",
        "email": "Preeti@atypicaladvantage.in",
        "location_preference": "Hyderabad",
        "disability": "None",
        "educational_qualification": "Bachelors",
        "work_experience": "4",
        "summary": "Recuiter with 4 years of experience in recruitment and talent management.",
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
        "summary": "Top recuiter with 3 years of experience in sourcing and hiring top talent.",
        "id": "600"
    }
]

# --------------------------------
# Session State
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
st.title("🤖 AI Candidate Outreach")

# --------------------------------
# Health Check
# --------------------------------
with st.sidebar:
    if st.button("Check API Health"):
        r = requests.get(HEALTH_URL)
        st.json(r.json())

# --------------------------------
# Job Description
# --------------------------------
job_desc = st.text_area("Job Description", "We are hiring a recruiter with 3–5 years experience.")

# --------------------------------
# Search Candidates (hardcoded)
# --------------------------------
if st.button("🔍 Search Candidates"):
    st.session_state.candidates = hardcoded_candidates

if st.session_state.candidates:
    df = pd.DataFrame(st.session_state.candidates)

    st.subheader("Candidate List")

    selected_rows = st.data_editor(
        df,
        width=1200,
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Name"),
            "email": st.column_config.TextColumn("Email"),
            "location_preference": "Location",
            "educational_qualification": "Education",
            "work_experience": "Experience",
            "summary": "Summary"
        },
        key="candidate_table"
    )

    st.session_state.selected = st.multiselect(
        "Select candidates to email",
        options=df["email"].tolist()
    )

    st.info(f"Selected {len(st.session_state.selected)} candidates")

# --------------------------------
# Generate Emails
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
            r = requests.post(CREATE_URL, json=payload)
            data = r.json()

            if data.get("success"):
                st.session_state.generated_emails = data["emails"]
                st.session_state.job_id = data["job_id"]
                st.success(f"Generated {len(data['emails'])} personalized emails")
            else:
                st.error(data.get("error"))

# --------------------------------
# Preview & Edit
# --------------------------------
if st.session_state.generated_emails:
    st.subheader("✏️ Review Emails")

    for i, email in enumerate(st.session_state.generated_emails):
        with st.expander(email["email"]):
            email["subject"] = st.text_input("Subject", email["subject"], key=f"s{i}")
            email["body"] = st.text_area("Body", email["body"], height=200, key=f"b{i}")

# --------------------------------
# Send Emails
# --------------------------------
if st.button("✅ Send Emails"):
    if not st.session_state.generated_emails:
        st.error("No emails generated")
    else:
        payload = {
            "job_id": st.session_state.job_id,
            "emails": st.session_state.generated_emails
        }

        with st.spinner("Sending emails..."):
            r = requests.post(SEND_URL, json=payload)
            data = r.json()

            if data.get("success"):
                st.success(f"Sent {data['emails_sent']} emails")
                st.session_state.generated_emails = []
            else:
                st.error(data.get("error"))
