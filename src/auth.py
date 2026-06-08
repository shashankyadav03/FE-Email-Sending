import os
import streamlit as st


def check_password() -> bool:
    """
    Returns True once the user has entered the correct APP_PASSWORD.
    If APP_PASSWORD is not set, skips the gate (dev mode).
    """
    app_password = os.getenv("APP_PASSWORD", "")
    if not app_password:
        return True

    if st.session_state.get("_authenticated"):
        return True

    # ── Centered login card ──────────────────────────────────────
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > .main { background: #F1F5F9; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:32px">
            <div style="font-size:52px">📧</div>
            <h1 style="font-size:28px;font-weight:800;color:#1E293B;margin:8px 0 4px">
                DataFinsight
            </h1>
            <p style="color:#64748B;font-size:15px;margin:0">Recruiter · Internal Dashboard</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            pwd = st.text_input(
                "Access Key",
                type="password",
                placeholder="Enter your access key...",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if pwd == app_password:
                st.session_state["_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect access key. Please try again.")

        st.markdown("""
        <p style="text-align:center;color:#94A3B8;font-size:12px;margin-top:24px">
            Internal use only · Contact your administrator for access
        </p>
        """, unsafe_allow_html=True)

    return False
