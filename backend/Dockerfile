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
# Install Walrus CLI (GitHub binary)
# ============================
RUN npm install -g @walrus/cli

# ============================
# Install SUI CLI
# ============================
RUN wget https://github.com/MystenLabs/sui/releases/download/testnet-v1.36.0/sui-testnet-x86_64-linux-gnu.tgz && \
    tar xvf sui-testnet-x86_64-linux-gnu.tgz && \
    mv sui-testnet-x86_64-linux-gnu/sui /usr/local/bin/sui && \
    chmod +x /usr/local/bin/sui && \
    rm -rf sui-testnet-x86_64-linux-gnu.tgz sui-testnet-x86_64-linux-gnu

# ============================
# Set working directory
# ============================
WORKDIR /app

# ============================
# Copy backend folder into image
# ============================
COPY . /app

# ============================
# Install Node dependencies for Seal client
# ============================
RUN cd services && \
    npm init -y && \
    npm install @mysten/sui @mysten/seal

# ============================
# Install Python dependencies
# ============================
RUN pip install --no-cache-dir -r requirements.txt

# ============================
# Expose port (Render uses $PORT)
# ============================
ENV PORT=10000
EXPOSE 10000

# ============================
# Start FastAPI server
# ============================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
