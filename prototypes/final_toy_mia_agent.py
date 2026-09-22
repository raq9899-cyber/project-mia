"""
Toy MIA Agent

Purpose:
  Evolve the original Step 1 prototype into a slightly richer Sprint 1 workflow
  without adding unnecessary complexity.

What this version does:
  1. Accepts an investor inquiry and basic sender context
  2. Classifies the inquiry (topic, risk, priority)
  3. Drafts an answer using ONLY the provided company document
  4. Requires human approval/rejection before completion
  5. Saves approved responses to a local JSON file as a primitive
     Approved Response Library / institutional memory

What this version intentionally does NOT do yet:
  - No vector database
  - No document chunking / embeddings
  - No semantic precedent search
  - No automatic email sending
  - No multi-agent orchestration
  - No production database

Setup:
    pip install langgraph langchain-openai
    export OPENAI_API_KEY="your-key-here"

Run:
    python prototypes/final_toy_mia_agent.py
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI


# ---------------------------------------------------------------------------
# 1. STATE: shared object passed between every workflow node
# ---------------------------------------------------------------------------
class MIAState(TypedDict):
    # Inquiry context
    sender_name: str
    organization: str
    relationship: str
    question: str

    # Knowledge used for drafting
    document: str

    # MIA classifications
    topic: str
    risk_level: str
    risk_reason: str
    priority_level: str
    priority_reason: str

    # Draft / review lifecycle
    answer: str
    approved: bool
    review_status: str

    # Institutional-memory output
    saved_record_id: str


# ---------------------------------------------------------------------------
# 2. STAND-IN KNOWLEDGE BASE
#    Later this becomes real filing / transcript retrieval.
# ---------------------------------------------------------------------------
SAMPLE_DOCUMENT = """
Q3 2026 Earnings Highlights (sample, for testing only):
- Revenue: $142M, up 18% year-over-year
- Gross margin: 61%, up from 58% in Q3 2025
- Long-term revenue growth target: 15-20% annually, reaffirmed this quarter
- Management cited pricing discipline and product mix as the primary
  drivers of margin expansion
"""


# ---------------------------------------------------------------------------
# 3. SIMPLE LOCAL APPROVED RESPONSE LIBRARY
#    This is intentionally JSON for the prototype. A real database comes later.
# ---------------------------------------------------------------------------
APPROVED_RESPONSES_FILE = Path("approved_responses.json")


def load_approved_responses() -> list[dict]:
    if not APPROVED_RESPONSES_FILE.exists():
        return []

    try:
        return json.loads(APPROVED_RESPONSES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_approved_response(record: dict) -> None:
    records = load_approved_responses()
    records.append(record)
    APPROVED_RESPONSES_FILE.write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 4. MODEL
# ---------------------------------------------------------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ---------------------------------------------------------------------------
# 5. NODE 1: classify inquiry
# ---------------------------------------------------------------------------
def classify_node(state: MIAState) -> dict:
    prompt = f"""You are helping triage investor-relations inquiries.

Classify the inquiry below.

Return exactly four lines in this format:
TOPIC: <short topic>
RISK: <Low, Medium, or High>
RISK_REASON: <one short sentence>
PRIORITY: <Low, Medium, or High>

Guidelines for this prototype:
- High risk: likely disclosure-sensitive subjects such as M&A, financing,
  litigation, unpublished guidance, MNPI, or requests for nonpublic information.
- Medium risk: interpretive financial or strategic questions that require care.
- Low risk: straightforward public-information questions.
- Priority should consider relationship context and apparent urgency, but do
  not invent facts that are not supplied.

Sender: {state['sender_name']}
Organization: {state['organization']}
Relationship: {state['relationship']}
Inquiry: {state['question']}
"""

    response = llm.invoke(prompt).content

    parsed = {
        "topic": "Unclassified",
        "risk_level": "Medium",
        "risk_reason": "Classification output could not be parsed reliably.",
        "priority_level": "Medium",
        "priority_reason": "Initial prototype default.",
    }

    for line in response.splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip().upper()
        value = value.strip()

        if key == "TOPIC":
            parsed["topic"] = value
        elif key == "RISK":
            parsed["risk_level"] = value
        elif key == "RISK_REASON":
            parsed["risk_reason"] = value
        elif key == "PRIORITY":
            parsed["priority_level"] = value

    parsed["priority_reason"] = (
        f"Prototype priority based on relationship '{state['relationship']}' "
        f"and inquiry context."
    )

    return parsed


# ---------------------------------------------------------------------------
# 6. NODE 2: draft answer strictly from supplied document
# ---------------------------------------------------------------------------
def answer_node(state: MIAState) -> dict:
    prompt = f"""You are an investor-relations assistant.

Answer the investor's question using ONLY the information in the document
below. If the document does not contain enough information, say clearly that
you do not have sufficient support from the supplied source.

Do not use outside knowledge. Do not invent facts.

DOCUMENT:
{state['document']}

QUESTION:
{state['question']}

RISK CLASSIFICATION:
{state['risk_level']} — {state['risk_reason']}
"""

    response = llm.invoke(prompt)
    return {"answer": response.content, "review_status": "Under Review"}


# ---------------------------------------------------------------------------
# 7. NODE 3: human approval gate
# ---------------------------------------------------------------------------
def approval_node(state: MIAState) -> dict:
    print("\n" + "=" * 70)
    print("MIA INQUIRY REVIEW")
    print("=" * 70)
    print(f"Sender:       {state['sender_name']}")
    print(f"Organization: {state['organization']}")
    print(f"Relationship: {state['relationship']}")
    print(f"Topic:        {state['topic']}")
    print(f"Risk:         {state['risk_level']} — {state['risk_reason']}")
    print(f"Priority:     {state['priority_level']} — {state['priority_reason']}")
    print("-" * 70)
    print("ORIGINAL INQUIRY:")
    print(state["question"])
    print("-" * 70)
    print("MIA DRAFT RESPONSE:")
    print(state["answer"])
    print("=" * 70)

    decision = input("Approve this answer? (y/n): ").strip().lower()

    if decision == "y":
        return {"approved": True, "review_status": "Approved"}

    return {"approved": False, "review_status": "Rejected"}


# ---------------------------------------------------------------------------
# 8. NODE 4: save approved response into primitive institutional memory
# ---------------------------------------------------------------------------
def save_node(state: MIAState) -> dict:
    if not state["approved"]:
        return {"saved_record_id": ""}

    record_id = datetime.now(timezone.utc).strftime("MIA-%Y%m%d-%H%M%S")

    record = {
        "record_id": record_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sender_name": state["sender_name"],
        "organization": state["organization"],
        "relationship": state["relationship"],
        "original_question": state["question"],
        "topic": state["topic"],
        "risk_level": state["risk_level"],
        "risk_reason": state["risk_reason"],
        "priority_level": state["priority_level"],
        "approved_answer": state["answer"],
        "status": "Approved",
        "source": "SAMPLE_DOCUMENT",
    }

    save_approved_response(record)
    return {"saved_record_id": record_id}


# ---------------------------------------------------------------------------
# 9. WIRE THE GRAPH
# ---------------------------------------------------------------------------
graph = StateGraph(MIAState)

graph.add_node("classify", classify_node)
graph.add_node("answer", answer_node)
graph.add_node("approval", approval_node)
graph.add_node("save", save_node)

graph.set_entry_point("classify")
graph.add_edge("classify", "answer")
graph.add_edge("answer", "approval")
graph.add_edge("approval", "save")
graph.add_edge("save", END)

app = graph.compile()


# ---------------------------------------------------------------------------
# 10. RUN IT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY before running this script.")
        raise SystemExit(1)

    print("\nToy MIA Agent v2")
    print("----------------")

    sender_name = input("Investor / sender name: ").strip() or "Unknown"
    organization = input("Organization: ").strip() or "Unknown"
    relationship = input(
        "Relationship (e.g. shareholder, analyst, prospect, unknown): "
    ).strip() or "Unknown"
    question = input("Investor question: ").strip()

    result = app.invoke({
        "sender_name": sender_name,
        "organization": organization,
        "relationship": relationship,
        "question": question,
        "document": SAMPLE_DOCUMENT,
        "topic": "",
        "risk_level": "",
        "risk_reason": "",
        "priority_level": "",
        "priority_reason": "",
        "answer": "",
        "approved": False,
        "review_status": "Received",
        "saved_record_id": "",
    })

    print("\n" + "=" * 70)
    if result["approved"]:
        print("APPROVED")
        print(f"Saved to institutional memory as {result['saved_record_id']}.")
        print(f"Library file: {APPROVED_RESPONSES_FILE.resolve()}")
    else:
        print("NOT APPROVED")
        print("Nothing was added to the Approved Response Library.")
    print("=" * 70)
