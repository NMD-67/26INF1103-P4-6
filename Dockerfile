FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tele/ ./tele/
COPY database/ ./database/
COPY Matching/ ./Matching/
COPY main.py io_manager.py logic_manager.py profile_schema.py profile_matching_AI.py ./

CMD ["python", "-m" , "tele.bot"]
