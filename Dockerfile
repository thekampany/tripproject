
FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

RUN python manage.py collectstatic --noinput

EXPOSE 8043

#CMD ["python", "manage.py", "runserver", "0.0.0.0:8043"]
CMD ["uvicorn", "tripproject.asgi:application", "--host", "0.0.0.0", "--port", "8043"]
