FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt ./

ENV PYTHONUNBUFFERED=1

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ./

ENTRYPOINT ["celery", "-A", "celery_app", "worker", "--loglevel=info", "-c", "4"]