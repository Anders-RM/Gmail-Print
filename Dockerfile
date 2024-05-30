# Use the official Python image from the Docker Hub
FROM python:slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV ACCOUNT_EMAIL=your-email@gmail.com
# Default to 300 seconds (5 minutes) if not set
ENV FETCH_INTERVAL=300  

# Run the application
CMD ["python", "print_emails.py"]
