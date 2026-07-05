FROM python:3.11-slim 

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /usr/src/app

COPY save_version.sh /usr/src/app/save_version.sh
RUN chmod +x /usr/src/app/save_version.sh
RUN mkdir -p /usr/src/app/media/exports /usr/src/app/staticfiles && chmod -R 777 /usr/src/app/media

ENV DJANGO_SETTINGS_MODULE=tripproject.settings
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y procps wget && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

COPY entrypoint.sh /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["uvicorn", "tripproject.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
