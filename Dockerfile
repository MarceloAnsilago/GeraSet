FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY flask_version/requirements-flask.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY flask_version /app/flask_version
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "12", "--timeout", "90", "flask_version.app:app"]
