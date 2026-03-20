FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git for cloning, curl for healthchecks, docker cli for sibling container access)
RUN apt-get update && \
    for i in 1 2 3 4 5; do \
        apt-get install -y --fix-missing \
            git \
            curl \
            ca-certificates \
            gnupg && break || sleep 10; \
    done && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    for i in 1 2 3 4 5; do \
        apt-get install -y --fix-missing docker-ce-cli && break || sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 bcrypt==4.0.1
RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 -r requirements.txt

# Final verification of mission-critical dependencies
RUN python -c "import jose; import bcrypt; import sqlalchemy; print('Dependencies verified')"

# Copy app source
COPY . .

# Ensure audit_reports dir is writable
RUN mkdir -p audit_reports && chmod 777 audit_reports

EXPOSE 8000

# Default to starting the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
