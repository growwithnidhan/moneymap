# Use Python base image
FROM python:3.11

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Run the app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]