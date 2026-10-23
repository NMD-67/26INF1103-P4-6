FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tele/ ./tele/
COPY database/ ./database/
COPY Data_Manager/ ./Data_Manager/
COPY AI_Manager/ ./AI_Manager/
COPY Matching/ ./Matching/
COPY IO_Manager/ ./IO_Manager/
COPY Logic_Manager/ ./Logic_Manager/
COPY main.py ./

CMD ["python", "-m" , "tele.bot"]
