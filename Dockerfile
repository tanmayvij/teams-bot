# Use small Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy dependency file first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy env file
COPY .env .env

# Run the worker
CMD ["python", "main.py"]