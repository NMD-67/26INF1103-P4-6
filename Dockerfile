FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tele/ ./tele/
COPY database/ ./database/

CMD ["python", "-m" , "tele.bot"]