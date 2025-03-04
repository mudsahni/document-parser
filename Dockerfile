FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Set env to test
ENV ENV=PROD

# Install necessary SSL packages and update certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        openssl \
        curl \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the service account key into the Docker container
COPY ./secrets/gcp-service-account-key.json src/application_default_credentials.json

# Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to point to the key file
ENV GOOGLE_APPLICATION_CREDENTIALS="src/application_default_credentials.json"
# Update pip and install certificates
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir certifi

# Copy requirements file
COPY src/requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Add necessary additional packages
RUN pip3 install --no-cache-dir gevent backoff

# Copy the rest of your application code into the container
COPY src /app/

# Set environment variable for SSL verification
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONHTTPSVERIFY=1

# Create an optimized gunicorn config
RUN echo "import multiprocessing\n\
\n\
# Bind to all addresses on port 8080 (Cloud Run default)\n\
bind = '0.0.0.0:8080'\n\
\n\
# Set worker class to Gevent for async capability\n\
worker_class = 'gevent'\n\
\n\
# Number of worker processes based on CPU cores\n\
workers = (2 * multiprocessing.cpu_count()) + 1\n\
\n\
# Number of threads per worker\n\
threads = 4\n\
\n\
# Worker timeout (in seconds)\n\
timeout = 300  # 5 minutes\n\
\n\
# Maximum number of requests a worker will process before restarting\n\
max_requests = 1000\n\
max_requests_jitter = 50\n\
\n\
# Logging configurations\n\
accesslog = '-'  # stdout\n\
errorlog = '-'   # stderr\n\
loglevel = 'info'\n\
\n\
# Keep-alive timeout\n\
keepalive = 65\n\
\n\
# Graceful timeout\n\
graceful_timeout = 60\n" > gunicorn_config.py

# Expose port
EXPOSE 8080

# Command to run Gunicorn with config file
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]