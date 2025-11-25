# ============================
# BASE IMAGE
# ============================
FROM python:3.10-slim

# ============================
# Install required system packages
# ============================
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ============================
# Install Node.js 18
# ============================
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get update && apt-get install -y nodejs

# ============================
# Install Walrus CLI (stable)
# ============================
RUN curl -sSf https://walrus.sh/install.sh | sh && \
    mv /root/.walrus/bin/walrus /usr/local/bin/walrus && \
    chmod +x /usr/local/bin/walrus

# ============================
# Install SUI CLI
# ============================
RUN wget https://github.com/MystenLabs/sui/releases/download/testnet-v1.36.0/sui-testnet-x86_64-linux-gnu.tgz && \
    tar xvf sui-testnet-x86_64-linux-gnu.tgz && \
    mv sui-testnet-x86_64-linux-gnu/sui /usr/local/bin/sui && \
    chmod +x /usr/local/bin/sui && \
    rm -rf sui-testnet-x86_64-linux-gnu*


# ============================
# Working directory
# ============================
WORKDIR /app

# ============================
# Copy backend ONLY
# ============================
COPY . /app

# ============================
# Install Node dependencies for Seal client
# ============================
RUN cd /app/services && \
    npm init -y && \
    npm install @mysten/sui @mysten/seal

# ============================
# Install Python dependencies
# ============================
RUN pip install --no-cache-dir -r requirements.txt

# ============================
# Expose port
# ============================
ENV PORT=10000
EXPOSE 10000

# ============================
# Start FastAPI
# ============================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
