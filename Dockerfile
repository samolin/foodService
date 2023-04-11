FROM python:3.11

WORKDIR /app

COPY ./foodService /app
COPY ./requirements.txt ./
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir -r requirements.txt
