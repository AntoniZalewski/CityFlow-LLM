FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/cityflow-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/cityflow-api /app
COPY examples /app/examples

EXPOSE 8000

CMD ["uvicorn", "cityflow_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
