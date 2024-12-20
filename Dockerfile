# Use official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Expose the port (if needed)
EXPOSE 8080

# Command to run the bot
CMD ["python3", "bot.py"]
