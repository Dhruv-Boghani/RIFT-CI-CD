FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git is needed for gitpython)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git config --global user.name "Dhruv"
RUN git config --global user.email "dhruvboghani624@gmail.com"

# Copy backend requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ ./backend/

# Set Python path to include /app so backend package is found
ENV PYTHONPATH=/app

# Default port for Render
ENV PORT=10000

# Run the application
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
