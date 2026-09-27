FROM python:3.11-slim
WORKDIR /app
COPY "Modular_auditor.py" .
CMD ["python", "Modular_auditor.py"]
