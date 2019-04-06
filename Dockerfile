FROM python:3-slim
WORKDIR /service
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y build-essential
RUN pip3 install -r requirements.txt
USER root
EXPOSE 8000
CMD PYTHONUNBUFFERED=1 gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 5 scoreboard.app:app -b 0.0.0.0 --capture-output

