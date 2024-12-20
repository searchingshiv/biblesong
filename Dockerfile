# Use official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /usr/src/app

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Expose the port (if needed)
EXPOSE 8080

# Command to run the bot
CMD ["python3", "bot.py"]
