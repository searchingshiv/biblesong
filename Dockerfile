# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
# ENV PYTHONUNBUFFERED 1
# ENV PYTHONDONTWRITEBYTECODE 1

# Set the working directory
WORKDIR /app

# Install system dependencies, including git
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir git+https://github.com/pytgcalls/pytgcalls.git

# Copy project files into the container
COPY . /app/

# Expose the Flask app's port
EXPOSE 8080

# Command to run the application
CMD ["python", "bot.py"]
