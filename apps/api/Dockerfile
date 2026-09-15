FROM smallstep/step-ca:0.30.2 AS step_cli

FROM python:3.12-slim

COPY --from=step_cli /usr/local/bin/step /usr/local/bin/step

WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/opt/venv/bin:$PATH"

COPY app ./app
COPY tests ./tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
