FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8550 \
    FOODPASS_ENV=production \
    FOODPASS_DATA_DIR=/app/data \
    FOODPASS_STUDENTS_CSV=/app/data/estudiantes.csv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libzbar0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY Backend ./Backend
COPY DATABASE ./DATABASE
COPY FRONTEND ./FRONTEND
COPY start_app.py .

RUN useradd --system --uid 10001 --create-home foodpass \
    && mkdir -p /app/data \
    && chown -R foodpass:foodpass /app

USER foodpass

EXPOSE 8550

CMD ["python", "start_app.py"]
