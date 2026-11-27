# Приложение «Цифровой механик». BASE можно заменить на заранее собранный образ с теми же зависимостями.
ARG BASE=python:3.12-slim
FROM ${BASE}
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HOME=/opt/hf
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt \
 && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
COPY app ./app
COPY web ./web
# заглушки заказчика: перед сборкой python -m tools.fetch_materials (в Git их нет)
COPY mocks ./mocks
# сервис работает не от root; данные (руководства, индекс, журнал) монтируются томом /app/data
ARG APP_UID=1000
RUN useradd --system --uid ${APP_UID} --home-dir /app mechanic && mkdir -p /app/data/state /opt/hf && chown -R mechanic /app/data /opt/hf
USER mechanic
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
