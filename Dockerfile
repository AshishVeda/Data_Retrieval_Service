FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create directory for ChromaDB data
RUN mkdir -p /data/chroma

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python packages with retry mechanism
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --timeout 100 --retries 3

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV CHROMA_DB_DIR=/data/chroma

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--timeout", "300", "--bind", "0.0.0.0:5000", "app:create_app()"]