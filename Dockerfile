# Use an official Python runtime as a base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements file to install dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code to the container
COPY . .

# Set environment variables (replace YOUR_DISCORD_TOKEN with your actual token or use a secret management system)
ENV DISCORD_TOKEN=$DISCORD_TOKEN

# Command to run the bot
CMD ["python", "bot.py"]
