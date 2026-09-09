FROM mcr.microsoft.com/devcontainers/python:3.12

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN sudo apt update && sudo apt install -y poppler-utils && sudo rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip