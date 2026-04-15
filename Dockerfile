FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_DEFAULT_TIMEOUT=300 \
  PIP_RETRIES=10

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --default-timeout=300 --retries=10 -r /app/requirements.txt

COPY . /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
