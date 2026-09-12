FROM python:3.9-slim

WORKDIR /workspace

# Install system dependencies required for some python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python packaging files
COPY pyproject.toml setup.cfg setup.py ./
COPY src/ ./src/

# Install the dependencies and the package itself
RUN pip install --no-cache-dir -e .

# Copy the rest of the project
COPY . .

EXPOSE 8888

# Run the all-in-one setup (data generation + model training + UI launch)
CMD ["python", "setup_and_run.py"]
