# Use the official Python image as the base image
FROM python:3

# Set the working directory inside the container
WORKDIR /tests

# Copy your application code into the container
COPY ib_client_test.py .

# Install the Python dependencies
RUN pip install requests
