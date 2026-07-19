FROM python:3.13-slim

WORKDIR /opt/neo
COPY pyproject.toml ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

WORKDIR /workspace
