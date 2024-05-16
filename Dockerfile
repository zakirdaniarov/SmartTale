FROM python:3.11.1

ENV APP_HOME /app

WORKDIR $APP_HOME

COPY ./requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get -y dist-upgrade && apt-get install -y netcat

COPY . .
RUN chmod +x ./entrypoint.sh
