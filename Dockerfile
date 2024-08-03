# Gebruik een officiële Python runtime als parent image
FROM python:3.9

# Stel de werkdirectory in
WORKDIR /usr/src/app

# Kopieer de vereisten-bestand in de container
COPY requirements.txt ./

# Installeer de dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de rest van de applicatie
COPY . .

# Stel de environment variables in
ENV PYTHONUNBUFFERED=1

EXPOSE 8043

# Voer de server uit
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8043"]
CMD ["uvicorn", "tripproject.asgi:application", "--host", "0.0.0.0", "--port", "8043"]
