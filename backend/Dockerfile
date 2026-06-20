# Use official lightweight Python image.
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=5000

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Expose the application port
EXPOSE 5000

# Run gunicorn server invoking the create_app factory
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 0 "app:create_app()"
