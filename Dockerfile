# Use a lightweight Python base
FROM python:3.10-slim

# Install FFmpeg (The magic step)
RUN apt-get update && apt-get install -y ffmpeg

# Set up the app folder
WORKDIR /app

# Copy files and install libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Run the app using Gunicorn on the port Render gives us
CMD gunicorn app:app --bind 0.0.0.0:$PORT