FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

RUN pip install playwright
# Install Playwright browsers
RUN playwright install --with-deps chromium

# Create logs directory
RUN mkdir -p logs

# Create a non-root user for running the application
RUN useradd --create-home --shell /bin/bash --uid 1000 --user-group appuser

# Change ownership of the application directory to the appuser
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application with multiple workers for production
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
