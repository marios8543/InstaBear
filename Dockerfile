FROM python:alpine3.7

RUN apk add build-base
RUN apk add libffi-dev
RUN apk add openssl-dev
RUN apk add python3-dev

COPY ./requirements.txt /
RUN pip install -r /requirements.txt

COPY . /app
WORKDIR /app
ENV PYTHONUNBUFFERED=0
EXPOSE 5000

CMD python3 -u main.py
