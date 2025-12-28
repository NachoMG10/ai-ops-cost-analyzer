FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for healthchecks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy dummy data file
COPY dummy_data.csv .

# Copy application code
COPY app/ ./app/

# Expose port (Coolify will map this automatically)
EXPOSE 8000

# Health check for Coolify
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set default port (Coolify may override with PORT env var)
ENV PORT=8000

# Run the application
# Coolify will set PORT env var, but we default to 8000 if not set
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
