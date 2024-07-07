# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY ./requirements.txt /app/requirements.txt

# Install the dependencies specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the rest of the application code into the container
COPY ./dashboard.py /app/dashboard.py
COPY ./config.env /app/config.env
COPY ./utils.py /app/utils.py

# Expose the port the app runs on
EXPOSE 8050

# Define the environment variable for the Flask server
ENV FLASK_APP=dashboard.py

# Command to run the application
CMD ["python", "dashboard.py"]
