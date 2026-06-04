FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py .
COPY enfa/__init__.py       ./enfa/__init__.py
COPY enfa/mongo.py          ./enfa/mongo.py
COPY dashboard/__init__.py  ./dashboard/__init__.py
COPY dashboard/pipeline.py  ./dashboard/pipeline.py
COPY scheduler/scheduler.py ./scheduler.py
COPY scheduler/settings.py  ./settings.py

CMD ["python", "scheduler.py"]