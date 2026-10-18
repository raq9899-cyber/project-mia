import os
import subprocess
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

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
                        st.subheader("MIA Draft Response")
                        st.text(result.stdout)
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

st.divider()
st.caption(
    "All responses require human review "
    "before external use."
)
