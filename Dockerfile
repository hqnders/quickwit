# Use an official Python runtime as a base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements file to install dependencies
COPY requirements.txt resources quickwit .
VOLUME data

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the bot
CMD ["python", "-m", "quickwit"]
