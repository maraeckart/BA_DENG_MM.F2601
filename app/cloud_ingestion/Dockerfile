FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir google-cloud-storage

COPY upload_to_gcs.py .

CMD ["python", "upload_to_gcs.py"]
