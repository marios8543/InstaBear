FROM python:alpine3.7

RUN apk add build-base
RUN apk add libffi-dev
RUN apk add openssl-dev
RUN apk add python3-dev

COPY . /app
WORKDIR /app
ENV stories_per_file 1000
RUN pip install -r requirements.txt
EXPOSE 5000

CMD python3 main.py
