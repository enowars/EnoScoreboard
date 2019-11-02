FROM python:3.7-slim
WORKDIR /service
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y build-essential
RUN pip3 install -r requirements.txt
USER root
CMD PYTHONUNBUFFERED=1 python scoreboard/app.py
