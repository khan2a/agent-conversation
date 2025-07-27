# Use official Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


# Install uv (Python dependency manager)
RUN pip install uv

# Install Python dependencies using uv
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Copy the application code (for build, but will be mounted in compose)
COPY . .

# Expose port 8000
EXPOSE 8000

# Set environment variables for FastAPI
ENV PYTHONUNBUFFERED=1

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
