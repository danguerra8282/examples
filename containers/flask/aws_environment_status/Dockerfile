# syntax=docker/dockerfile:1

# Defines Docker Image to use
FROM python:3.8-slim-buster

# Defines the working directory inside the container
WORKDIR /_aws_environment_status

# Copy the contents of the requirements.txt to the container
COPY requirements.txt requirements.txt

# Install the requirements on the container
RUN pip3 install -r requirements.txt

# Copy the rest of the contents from the local folder to the container's working directory
COPY . .

# Instruct the container to run the Flask app as a module and makes the container externally available
CMD [ "python3", "-m", "flask", "run", "--host=0.0.0.0" ]

# The following commands will run the container after it is built and you can browse to the app via a internet browser
# sudo docker run -d -p 5000:5000 _aws_environment_status
# browse to: http://localhost:5000/
