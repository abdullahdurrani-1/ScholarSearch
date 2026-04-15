# 🎓 ScholarSearch | Production-Grade RAG for Knowledge

> **AI-Powered Semantic Search Over Academic Books with Grounded Citations**
>
> A full-stack Retrieval-Augmented Generation (RAG) system combining **Dense + Sparse Retrieval** with **Generative AI** to answer student questions with **source-verified citations** from trusted ML, DS, and DL textbooks.

---

## ✨ Why ScholarSearch?

### The Problem 🤔
Students get **fluent but ungrounded** answers from generic chatbots. They can't verify sources, understand reasoning, or learn from authoritative textbooks.

### The Solution 🚀
ScholarSearch answers with:
- ✅ **Hybrid Retrieval** (FAISS Dense + BM25 Sparse vectors merged via RRF)
- ✅ **Grounded Generation** (Google Gemini with source citations)
- ✅ **Production APIs** (FastAPI with auth, rate limits, metrics)
- ✅ **Interactive Dashboards** (Streamlit + HTML/CSS/JS)
- ✅ **Evaluation Gates** (Auto-validate retrieval & generation quality)

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                     📚 PDF Books Corpus                          │
│               (ML, DS, DL textbooks in books/)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │   🔄 Data Pipeline (PyMuPDF)     │
        │  → Extract + Clean + Tokenize    │
        └────────┬─────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
  🔢 Dense Index    📝 Sparse Index
  (FAISS SentenceT) (BM25)
        │                 │
        └────────┬────────┘
                 │
                 ▼
        ┌──────────────────────┐
        │  🎯 Hybrid Retrieval  │
        │   (RRF Fusion)       │
        └─────────┬────────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │  🤖 RAG Generation    │
        │  (Google Gemini)     │
        └─────────┬────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
   🔌 FastAPI  📊 Streamlit  🌐 HTML Dashboard
   (Backend)   (UI)         (Interactive)
```

---

## 🛠️ Tech Stack

| Component | Technology | Why? |
|-----------|-----------|------|
| **Parsing** | PyMuPDF | Fast PDF extraction, handles corrupted PDFs |
| **Chunking** | LangChain TextSplitter | Smart overlap, preserves context |
| **Dense Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Fast, semantic-aware, CPU-efficient |
| **Dense Index** | FAISS | Sub-millisecond retrieval at scale |
| **Sparse Index** | rank-bm25 | Handles acronyms, exact terms (BM25 TF-IDF) |
| **Fusion** | Reciprocal Rank Fusion (RRF) | Combines dense + sparse robustly |
| **Generation** | Google Gemini API | SOTA reasoning + grounding capability |
| **Backend** | FastAPI + Uvicorn | Async, auto-docs (OpenAPI), production-ready |
| **Frontend UI** | Streamlit | Rapid prototyping dashboard |
| **Dashboard** | HTML/CSS/JS + Chart.js | Deployable static interface |
| **Monitoring** | Prometheus + Grafana | Production metrics & alerting |
| **Testing** | pytest + evaluation harness | Quality gates for retrieval & generation |

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- **Python 3.11+** (tested on 3.11, works on 3.12+)
- **git**
- **Google API Key** (free tier at [Google AI Studio](https://aistudio.google.com/apikey))

### 1️⃣ Clone & Setup Environment

```bash
git clone https://github.com/your-username/scholarsearch.git
cd scholarsearch
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2️⃣ Configure Secrets

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

**Or set via environment:**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

### 3️⃣ Start the API Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

✅ **Dashboard available at:** `http://localhost:8000/`

### 4️⃣ (Optional) Run Streamlit UI

```bash
streamlit run frontend/app.py
```

### 5️⃣ (Optional) Run Evaluation Tests

```bash
python -m evaluation.run_eval
```

---

## 📡 API Endpoints

### Query RAG (Main Endpoint)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the backpropagation algorithm?",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "answer_id": "ans_abc123",
  "answer": "Backpropagation is...",
  "citations": [
    {
      "chunk_id": "chunk_42",
      "source": "Deep Learning Goodfellow p.204",
      "text": "..."
    }
  ],
  "retrieval_time_ms": 45,
  "generation_time_ms": 1200,
  "reranked_chunks": 5
}
```

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Metrics (Prometheus)
```bash
curl http://localhost:8000/metrics
```

### Submit Feedback
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the backpropagation algorithm?",
    "answer_id": "ans_abc123",
    "rating": 5,
    "comment": "Very helpful!"
  }'
```

Full API docs at: `http://localhost:8000/docs` (auto-generated OpenAPI)

---

## 📊 Project Structure

```
scholarsearch/
├── api/                          # 🔌 FastAPI backend
│   ├── app.py                    # Main API routes + startup
│   └── main.py                   # Entry point
├── frontend/                      # 🎨 UI Dashboards
│   ├── app.py                    # Streamlit app
│   └── dashboard.html            # Static HTML dashboard
├── generation/                    # 🤖 RAG Chain
│   └── rag_chain.py              # Gemini integration
├── retrieval/                     # 🎯 Hybrid Retrieval
│   ├── hybrid_retriever.py       # RRF fusion logic
│   └── vector_store.py           # FAISS + BM25 management
├── data_pipeline/                # 🔄 ETL (PDF → Chunks)
│   └── books/                    # 📚 Input PDFs
├── data/                         # 💾 Processed Data
│   ├── processed/
│   │   ├── chunks.json           # Chunked text corpus
│   │   ├── chunk_metadata.json   # Source + page numbers
│   │   ├── embeddings.npy        # Dense vectors (FAISS)
│   │   ├── faiss_index.bin       # FAISS index
│   │   └── bm25_corpus.pkl       # BM25 index
│   └── metadata/
│       ├── feedback.csv          # User ratings
│       └── request_logs.json     # Query history
├── evaluation/                    # ✅ Quality Gates
│   ├── run_eval.py               # Evaluation harness
│   └── eval_gate.py              # Recall/MRR/Groundedness
├── config/                        # ⚙️ Settings
│   └── settings.py               # Env vars + constants
├── ops/                          # 📈 DevOps
│   ├── monitoring/
│   │   ├── prometheus.yml        # Metrics config
│   │   └── grafana/              # Dashboards
│   └── docker-compose.yml        # Full stack deployment
├── tests/                        # 🧪 Tests
│   ├── test_eval_gate.py
│   ├── test_retrieval.py
│   └── demo_questions.py
├── notebooks/                    # 📓 Jupyter exploration
│   └── pdf_extraction_pymupdf.ipynb
├── ARCHITECTURE.md               # 🏛️ Deep dive docs
├── EXPERIMENTS.md                # 🧪 Benchmarks
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Full stack Docker
├── Dockerfile                    # API container
├── Dockerfile.frontend           # UI container
└── .env.example                  # Secrets template
```

---

## 🔄 Data Pipeline

### Step 1: Add Books
Place PDF files in `data_pipeline/books/`:
```bash
cp your_ml_book.pdf data_pipeline/books/
```

### Step 2: Generate Chunks & Embeddings
```bash
# (Coming soon: automated script)
# For now, embeddings are pre-computed in data/processed/
```

**Pre-computed data includes:**
- `chunks.json` - 5,000+ text segments
- `chunk_metadata.json` - Source tracking
- `embeddings.npy` - Dense vectors
- `faiss_index.bin` - Ready-to-query index
- `bm25_corpus.pkl` - Sparse index

---

## 🧪 Evaluation & Testing

### Run Quality Gates
```bash
python -m evaluation.run_eval
```

**Metrics Validated:**
- **Recall@5** - Does top-5 retrieval include ground truth? (target: 70%+)
- **MRR** (Mean Reciprocal Rank) - How highly ranked is the answer? (target: 40%+)
- **Groundedness** - Is generation supported by retrieved chunks? (target: 70%+)

### Demo Questions
```bash
python tests/demo_questions.py
```

Runs 10 sample queries to validate end-to-end system.

---

## 🐳 Docker Deployment

### Full Stack (API + Streamlit + Prometheus + Grafana)
```bash
docker compose up -d --build
```

**Access:**
- API: http://localhost:8000/
- Streamlit: http://localhost:8501/
- Prometheus: http://localhost:9090/
- Grafana: http://localhost:3000/ (user: `admin`, pass: `admin`)

### Stop Stack
```bash
docker compose down
```

---

## 📈 Monitoring & Observability

### Prometheus Metrics
- `scholarsearch_http_requests_total` - Request count by method/path/status
- `scholarsearch_request_duration_seconds` - Latency histogram
- `scholarsearch_queries_total` - Total /query calls
- `scholarsearch_index_ready` - System readiness (1=ready, 0=down)

### Sample Dashboard
Grafana dashboard JSON available at `ops/grafana/dashboards/scholarsearch-overview.json`

---

## 🔐 Security & Best Practices

✅ **Implemented:**
- Rate limiting (configurable limit/minute)
- JWT token auth for sensitive endpoints
- Request validation (Pydantic models)
- CORS middleware
- Environment secrets (API key not in code)

⚙️ **For Production:**
- Rotate `GOOGLE_API_KEY` regularly
- Enable HTTPS/TLS in reverse proxy
- Use managed secrets store (Vault, AWS Secrets Manager)
- Add request signing + audit logs
- Deploy with Kubernetes for auto-scaling

---

## 🧠 How It Works

### Query Flow
1. **User submits question** → FastAPI `/query` endpoint
2. **Embed question** → sentence-transformers
3. **Retrieve candidates:**
   - Dense search: FAISS k-NN (top 50)
   - Sparse search: BM25 (top 50)
   - Merge via RRF → top-5 chunks
4. **Generate answer** → Google Gemini (with chunk context)
5. **Attach citations** → Link chunks → source books
6. **Return JSON** → Frontend renders with UI

### Why Hybrid Retrieval?
- **Dense** catches semantic similarity (synonyms, paraphrasing)
- **Sparse** catches exact terms (names, acronyms)
- **RRF** combines both robustly without tuning weights

---

## 📊 Benchmarks

Run on `data/processed/` (5,000+ chunks, 12+ books):

| Task | Time |
|------|------|
| Question embedding | 5ms |
| Dense retrieval (FAISS) | 15ms |
| Sparse retrieval (BM25) | 20ms |
| RRF ranking | 2ms |
| **Total retrieval** | **~40ms** |
| Answer generation (Gemini) | 1.2s |
| **End-to-end query** | **~1.3s** |

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-idea`
3. Commit changes: `git commit -am 'Add feature'`
4. Push: `git push origin feature/your-idea`
5. Open a Pull Request

**Development Setup:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/
```

---

## 📜 License

This project is licensed under the **MIT License** — see `LICENSE` file for details.

**Data Attribution:**
- Book excerpts used for educational purposes
- Citations provided to original authors
- Comply with fair-use and educational licensing

---

## 🙋 FAQ

**Q: How do I add more books?**
A: Add PDFs to `data_pipeline/books/`, then re-generate embeddings (script coming soon). Pre-computed data already includes 5,000+ chunks.

**Q: What's the cost?**
A: Google Gemini API is free tier (60 calls/min). Beyond that, ~$0.075 per million input tokens.

**Q: Can I use a different LLM?**  
A: Yes! Swap `generation/rag_chain.py` to use OpenAI, Anthropic, or local LLMs (Ollama).

**Q: Does this work offline?**
A: Retrieval works offline (FAISS + BM25 are local). Generation requires API key (can't use without internet).

**Q: How do I deploy to production?**
A: Use Docker Compose or Kubernetes. Add a reverse proxy (Nginx), SSL certs, and managed secrets.

---

## 📞 Support

- **Issues:** Use GitHub Issues for bugs & feature requests
- **Discussions:** Community Q&A at GitHub Discussions
- **Email:** research@scholarsearch.dev (coming soon)

---

## 🌟 Acknowledgments

Built with:
- 🤗 **HuggingFace** (sentence-transformers)
- 🚀 **FastAPI** & **Streamlit** (frameworks)
- 🔍 **FAISS** & **rank-bm25** (retrieval)
- 🤖 **Google Gemini** (generation)
- 📊 **Prometheus** & **Grafana** (monitoring)

---

## 🚀 Roadmap

- [ ] Automated PDF ingestion pipeline
- [ ] Multi-modal retrieval (images, tables)
- [ ] Fine-tuned reranker (cross-encoder)
- [ ] Local LLM support (Ollama integration)
- [ ] Graph RAG (entity + relationship extraction)
- [ ] Multi-language support
- [ ] Chrome extension for inline search
- [ ] Mobile app (React Native)

---

<div align="center">

**Made with ❤️ for students and researchers**

⭐ Star us on GitHub if this helped!

[🔗 Live Demo](https://scholarsearch.dev) • [📖 Docs](https://docs.scholarsearch.dev) • [🐛 Report Bug](https://github.com/your-username/scholarsearch/issues)

</div>
