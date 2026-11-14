FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tele/ ./tele/
COPY Data_Manager/ ./Data_Manager/
COPY AI_Manager/ ./AI_Manager/
COPY IO_Manager/ ./IO_Manager/
COPY config/ ./config/
COPY Logic_Manager/ ./Logic_Manager/
COPY main.py sitogether_app.py automated_test_script.py ./
COPY ci/ ./ci/
COPY tests/test_mutual_preference_filter.py ./tests/test_mutual_preference_filter.py
COPY tests/test_birthday_privacy.py ./tests/test_birthday_privacy.py
COPY models/ ./models/
COPY results/ ./results/
COPY exceptions/ ./exceptions/

CMD ["python", "main.py"]
