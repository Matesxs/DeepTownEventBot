ARG PYTHON_VERSION=3.12.1
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE 1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED 1

WORKDIR /bot
VOLUME /bot

# Update packages
RUN apt-get update && apt-get upgrade -y

# Install external dependencies
RUN apt-get install build-essential libffi-dev libpq-dev git -y

# Install pip
RUN /usr/local/bin/python -m pip install --upgrade pip

# Copy the source code into the container.
COPY . .

# Install bot python dependencies
RUN python -m ensurepip --upgrade
RUN pip install --upgrade setuptools
RUN pip install --no-cache-dir -r requirements.txt --user

# Clean build tools
RUN apt-get --purge remove build-essential -y

# Set git safe directory
RUN git config --global --add safe.directory /bot

# Run the application.
CMD python bot.py
