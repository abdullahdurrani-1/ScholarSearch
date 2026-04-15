"""Production API entrypoint for ScholarSearch RAG services."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from typing import cast

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest  # type: ignore[reportMissingImports]
from pydantic import BaseModel, Field

from config.settings import (
    AUTH_DB_FILE,
    AUTH_TOKEN_TTL_HOURS,
    FEEDBACK_FILE,
    METADATA_DIR,
    PROCESSED_DIR,
    RATE_LIMIT_PER_MINUTE,
    REQUEST_LOG_FILE,
    TOP_K,
)
from generation.rag_chain import RagChain
from retrieval.hybrid_retriever import HybridRetriever


class QueryRequest(BaseModel):
    """Validates incoming question requests."""

    question: str = Field(min_length=10, max_length=500)
    top_k: int = Field(default=TOP_K, ge=1, le=10)
    session_id: int | None = None


class FeedbackRequest(BaseModel):
    """Validates user feedback payloads."""

    query: str = Field(min_length=1, max_length=500)
    answer_id: str = Field(min_length=1, max_length=128)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1500)


class RegisterRequest(BaseModel):
    """Validates account registration payloads."""

    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    """Validates account login payloads."""

    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=256)


class AppState:
    """In-memory runtime state for analytics and serving."""

    def __init__(self) -> None:
        self.retriever: HybridRetriever | None = None
        self.rag_chain: RagChain | None = None
        self.query_count = 0
        self.latencies: list[float] = []
        self.ratings: list[int] = []
        self.recent_queries: deque[str] = deque(maxlen=5)
        self.rate_limit_buckets: dict[str, deque[float]] = defaultdict(deque)


runtime = AppState()
app = FastAPI(title="ScholarSearch API", version="2.0.0")

REQUEST_COUNT = Counter(
    "scholarsearch_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "scholarsearch_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)
QUERY_COUNT_METRIC = Counter(
    "scholarsearch_queries_total",
    "Total number of /query calls",
)
INDEX_READY_GAUGE = Gauge(
    "scholarsearch_index_ready",
    "Whether retrieval index and generation chain are loaded (1 ready, 0 not ready)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    started = time.time()
    path = request.url.path
    method = request.method
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(time.time() - started)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str, salt: str) -> str:
    raw = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _ensure_metadata_paths() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_FILE.exists():
        FEEDBACK_FILE.write_text("timestamp,answer_id,rating,query,comment\n", encoding="utf-8")


def _init_auth_db() -> None:
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
        )
        """
    )
    conn.commit()
    conn.close()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    return authorization[len(prefix) :].strip()


def _resolve_user_id(authorization: str | None) -> int | None:
    token = _extract_bearer_token(authorization)
    if not token:
        return None

    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, expires_at FROM auth_tokens WHERE token = ?", (token,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None

    return int(row["user_id"])


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    bucket = runtime.rate_limit_buckets[client_ip]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: max 10 requests/minute per IP")
    bucket.append(now)


def _create_session_if_needed(user_id: int, question: str, session_id: int | None) -> int:
    conn = _db()
    cur = conn.cursor()

    if session_id is not None:
        cur.execute("SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        found = cur.fetchone()
        if found:
            conn.close()
            return int(found["id"])

    title = question[:80].strip() or "New Chat"
    cur.execute(
        "INSERT INTO chat_sessions (user_id, title, created_at) VALUES (?, ?, ?)",
        (user_id, title, _now_iso()),
    )
    conn.commit()
    if cur.lastrowid is None:
        conn.close()
        raise HTTPException(status_code=500, detail="Failed to create chat session")
    created_id = int(cast(int, cur.lastrowid))
    conn.close()
    return created_id


def _save_message(session_id: int, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_messages (session_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, json.dumps(metadata or {}), _now_iso()),
    )
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event() -> None:
    _ensure_metadata_paths()
    _init_auth_db()
    runtime.retriever = HybridRetriever(PROCESSED_DIR)
    runtime.rag_chain = RagChain(runtime.retriever)
    INDEX_READY_GAUGE.set(1)


@app.get("/")
def web_dashboard() -> FileResponse:
    dashboard_path = Path(__file__).resolve().parents[1] / "frontend" / "dashboard.html"
    return FileResponse(str(dashboard_path))


@app.get("/health")
def health() -> dict[str, Any]:
    index_ready = runtime.retriever is not None and runtime.rag_chain is not None
    chunks_loaded = runtime.retriever.vector_store.total_chunks if runtime.retriever else 0
    INDEX_READY_GAUGE.set(1 if index_ready else 0)
    return {"status": "ok", "chunks_loaded": chunks_loaded, "index_ready": index_ready}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/auth/register")
def register(payload: RegisterRequest) -> dict[str, Any]:
    email = _normalize_email(payload.email)
    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(payload.password, salt)

    conn = _db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, email, salt, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (payload.name.strip(), email, salt, pwd_hash, _now_iso()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Email already registered")

    if cur.lastrowid is None:
        conn.close()
        raise HTTPException(status_code=500, detail="Failed to create user")
    user_id = int(cast(int, cur.lastrowid))
    conn.close()
    return {"registered": True, "user_id": user_id, "name": payload.name.strip(), "email": email}


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    email = _normalize_email(payload.email)

    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, salt, password_hash FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expected_hash = _hash_password(payload.password, user["salt"])
    if expected_hash != user["password_hash"]:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_urlsafe(40)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=AUTH_TOKEN_TTL_HOURS)).isoformat()
    cur.execute(
        "INSERT OR REPLACE INTO auth_tokens (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (token, int(user["id"]), expires_at, _now_iso()),
    )
    conn.commit()
    conn.close()

    return {
        "token": token,
        "expires_at": expires_at,
        "user": {"id": int(user["id"]), "name": user["name"], "email": user["email"]},
    }


@app.get("/chat/sessions")
def list_sessions(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user_id = _resolve_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, created_at FROM chat_sessions WHERE user_id = ? ORDER BY id DESC LIMIT 100",
        (user_id,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return {"sessions": rows}


@app.get("/chat/session/{session_id}")
def get_session_messages(session_id: int, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user_id = _resolve_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    found = cur.fetchone()
    if not found:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    cur.execute(
        "SELECT id, role, content, metadata_json, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    )
    rows = []
    for row in cur.fetchall():
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        except json.JSONDecodeError:
            item["metadata"] = {}
        rows.append(item)
    conn.close()
    return {"messages": rows}


@app.post("/query")
def query(
    payload: QueryRequest,
    http_request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if runtime.rag_chain is None:
        raise HTTPException(status_code=503, detail="Service not ready. Retriever/model still loading.")

    client_ip = http_request.client.host if http_request.client else "unknown"
    _check_rate_limit(client_ip)

    started = time.time()
    result = runtime.rag_chain.generate_answer(payload.question, top_k=payload.top_k)
    latency = time.time() - started

    runtime.query_count += 1
    QUERY_COUNT_METRIC.inc()
    runtime.latencies.append(latency)
    runtime.recent_queries.append(payload.question)

    answer_id = f"ans_{int(started * 1000)}"
    chunk_ids = [c.get("chunk_id") for c in result.get("citations", []) if isinstance(c, dict)]

    user_id = _resolve_user_id(authorization)
    session_id = None
    if user_id is not None:
        session_id = _create_session_if_needed(user_id, payload.question, payload.session_id)
        _save_message(session_id, "user", payload.question)
        _save_message(
            session_id,
            "assistant",
            str(result.get("answer", "")),
            {
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", "medium"),
                "chunks_used": result.get("chunks_used", 0),
            },
        )

    log_record = {
        "timestamp": _now_iso(),
        "answer_id": answer_id,
        "query": payload.question,
        "latency_sec": round(latency, 4),
        "client_ip": client_ip,
        "chunk_ids": chunk_ids,
        "user_id": user_id,
        "session_id": session_id,
    }
    _append_jsonl(REQUEST_LOG_FILE, log_record)

    return {
        "answer_id": answer_id,
        "session_id": session_id,
        **result,
        "latency_sec": round(latency, 4),
    }


@app.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, bool]:
    safe_query = payload.query.replace("\n", " ").replace(",", " ")
    safe_comment = payload.comment.replace("\n", " ").replace(",", " ")
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"{_now_iso()},{payload.answer_id},{payload.rating},{safe_query},{safe_comment}\n"
        )

    runtime.ratings.append(payload.rating)
    return {"received": True}


@app.get("/stats")
def stats() -> dict[str, Any]:
    avg_latency = (sum(runtime.latencies) / len(runtime.latencies)) if runtime.latencies else 0.0
    avg_rating = (sum(runtime.ratings) / len(runtime.ratings)) if runtime.ratings else 0.0
    return {
        "total_queries": runtime.query_count,
        "avg_latency": round(avg_latency, 4),
        "avg_rating": round(avg_rating, 3),
        "recent_queries": list(runtime.recent_queries),
    }
