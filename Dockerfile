FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt ./

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip uninstall -y pytgcalls tgcalls && \
    pip install pytgcalls==0.0.5 tgcalls==0.0.3 TgCrypto && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Command to run the app
CMD ["python", "bot.py"]
