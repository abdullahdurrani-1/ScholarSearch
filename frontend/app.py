"""Streamlit UI for ScholarSearch that calls the FastAPI backend."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def _http_get(path: str) -> dict:
	req = Request(f"{API_BASE}{path}", method="GET")
	with urlopen(req, timeout=30) as response:
		return json.loads(response.read().decode("utf-8"))


def _http_post(path: str, payload: dict) -> dict:
	data = json.dumps(payload).encode("utf-8")
	req = Request(f"{API_BASE}{path}", data=data, method="POST")
	req.add_header("Content-Type", "application/json")
	with urlopen(req, timeout=120) as response:
		return json.loads(response.read().decode("utf-8"))


st.set_page_config(page_title="ScholarSearch - DS/ML Knowledge Assistant", layout="wide")

if "history" not in st.session_state:
	st.session_state.history = []
if "question" not in st.session_state:
	st.session_state.question = ""
if "result" not in st.session_state:
	st.session_state.result = None

st.title("ScholarSearch — DS/ML Knowledge Assistant")
st.caption("Grounded answers from your ML library")

col_main, col_side = st.columns([3, 1])

with col_side:
	st.subheader("System")
	try:
		health = _http_get("/health")
		stats = _http_get("/stats")
		status = "🟢 Ready" if health.get("index_ready") else "🔴 Not Ready"
		st.write(f"Status: {status}")
		st.write(f"Chunks loaded: {health.get('chunks_loaded', 0):,}")
		st.write(f"Total queries: {stats.get('total_queries', 0):,}")
		st.write(f"Avg latency: {stats.get('avg_latency', 0):.3f}s")
	except Exception:
		st.error("Backend unavailable at http://localhost:8000")

	st.subheader("Last 5 Queries")
	for item in st.session_state.history[-5:][::-1]:
		if st.button(item, key=f"history_{item}"):
			st.session_state.question = item

with col_main:
	st.subheader("Ask")
	st.session_state.question = st.text_input(
		"Question",
		value=st.session_state.question,
		placeholder="Ask anything about your ML books...",
		label_visibility="collapsed",
	)

	ask_col, reset_col = st.columns([1, 1])
	submitted = ask_col.button("Submit")
	reset_clicked = reset_col.button("Clear")

	if reset_clicked:
		st.session_state.question = ""
		st.session_state.result = None

	if submitted and st.session_state.question:
		with st.spinner("Searching books and generating grounded answer..."):
			try:
				result = _http_post("/query", {"question": st.session_state.question, "top_k": 5})
				st.session_state.result = result
				st.session_state.history.append(st.session_state.question)
			except HTTPError as e:
				body = e.read().decode("utf-8", errors="ignore")
				st.error(f"API error {e.code}: {body}")
			except URLError as e:
				st.error(f"Network error: {e}")
			except Exception as e:
				st.error(f"Unexpected error: {e}")

	if st.session_state.result:
		result = st.session_state.result
		st.subheader("Answer")
		st.info(result.get("answer", "No answer returned."))

		confidence = (result.get("confidence", "medium") or "medium").upper()
		color = {"HIGH": "green", "MEDIUM": "orange", "LOW": "red"}.get(confidence, "gray")
		st.markdown(f"**Confidence:** :{color}[{confidence}]")

		st.subheader("Citations")
		for idx, citation in enumerate(result.get("citations", []), start=1):
			with st.expander(
				f"📖 {idx}. {citation.get('book', 'Unknown')} | Page {citation.get('page', 'Unknown')} | Relevance: {citation.get('relevance', 'medium')}"
			):
				st.write(f"Chunk ID: {citation.get('chunk_id', 'n/a')}")

		st.subheader("Follow-up Questions")
		for follow_up in result.get("follow_up_questions", []):
			if st.button(follow_up, key=f"follow_{follow_up}"):
				st.session_state.question = follow_up

		st.subheader("Feedback")
		rating = st.slider("Rate this answer", min_value=1, max_value=5, value=4)
		comment = st.text_area("Comment", value="", placeholder="What should be improved?")
		if st.button("Send feedback"):
			try:
				_http_post(
					"/feedback",
					{
						"query": result.get("query", st.session_state.question),
						"answer_id": result.get("answer_id", "manual"),
						"rating": int(rating),
						"comment": comment,
					},
				)
				st.success("Feedback received.")
			except Exception as e:
				st.error(f"Could not send feedback: {e}")

st.caption("Answers grounded in loaded books only. Always verify with primary source.")
