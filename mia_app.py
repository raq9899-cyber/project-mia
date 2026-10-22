import os
import subprocess
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

if "draft_response" not in st.session_state:
    st.session_state.draft_response = ""

if "review_status" not in st.session_state:
    st.session_state.review_status = "Not reviewed"

st.set_page_config(
    page_title="MIA - Investor Relations Assistant",
    page_icon="💼",
    layout="wide"
)

st.title("MIA - Investor Relations Assistant")
st.caption("Ameresco | Internal Prototype")

st.divider()

question = st.text_area(
    "Investor Question",
    placeholder="What is Ameresco's outlook for 2026?",
    height=120
)

if st.button("Generate Response", type="primary"):
    if not question.strip():
        st.warning("Please enter an investor question.")
    else:
        required_keys = [
            "OPENAI_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_SECRET_KEY"
        ]

        missing = [
            key for key in required_keys
            if not os.environ.get(key)
        ]

        if missing:
            st.error(
                "Missing API configuration. Please check "
                "your terminal environment variables."
            )
        else:
            with st.spinner(
                "MIA is researching Ameresco documents..."
            ):
                try:
                    result = subprocess.run(
                        [
                            sys.executable,
                            "prototypes/mia_draft_response.py"
                        ],
                        input=question + "\n",
                        text=True,
                        capture_output=True,
                        timeout=120
                    )

                    if result.returncode != 0:
                        st.error("MIA could not generate a response.")
                        st.code(result.stderr)

                    else:
                        response_text = result.stdout

                        if "MIA — INVESTOR RELATIONS DRAFT" in response_text:
                            response_text = response_text.split(
                                "MIA — INVESTOR RELATIONS DRAFT", 1
                            )[1].strip()
                            if "Draft response:" in response_text:
                                response_text = response_text.split(
                                    "Draft response:", 1
                                )[1].strip()
                            if "[SOURCE 1]" in response_text:
                                response_text = response_text.split(
                                    "[SOURCE 1]", 1
                                )[0].strip()

                            if "STATUS: NOT APPROVED" in response_text:
                                response_text = response_text.split(
                                    "STATUS: NOT APPROVED", 1
                                )[0].strip()
                            st.session_state.draft_response = response_text
                            st.session_state.reviewed_response = response_text
                            st.session_state.review_status = "Pending review"

                            st.subheader("MIA Draft Response")
                            st.text(st.session_state.draft_response)
                            st.warning(
                                "NOT APPROVED — NOT SENT. "
                                "Human review is required."
                            )

                except subprocess.TimeoutExpired:
                    st.error(
                        "MIA took too long to respond. "
                        "Please try again."
                    )
                except Exception:
                    st.error(
                        "An unexpected error occurred."
                    )
if st.session_state.draft_response:
    st.subheader("Human Review")

    st.text_area(
        "Edit MIA's Response",
        height=300,
        key="reviewed_response"
    )

    
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Approve"):
            if st.session_state.reviewed_response.strip():
                st.session_state.review_status = "Approved"
                st.success("Response approved locally. Not sent.")
            else:
                st.error("Cannot approve an empty response.")

    with col2:
        if st.button("Request Revision"):
            st.session_state.review_status = "Needs revision"
            st.warning("Response returned for revision.")

    with col3:
        if st.button("Reject"):
            st.session_state.review_status = "Rejected"
            st.error("Response rejected.")

    st.info(
        f"Review Status: {st.session_state.review_status}"
    )

st.divider()
st.caption(
    "All responses require human review "
    "before external use."
)
