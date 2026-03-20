FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user (security best practice, avoids Cloud Run warnings)
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Document the port Cloud Run will use
EXPOSE 8080

ENV PORT=8080

CMD ["python", "main.py"]
