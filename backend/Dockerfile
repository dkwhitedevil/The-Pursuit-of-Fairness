# ============================
# BASE IMAGE
# ============================
FROM python:3.10-slim

# ============================
# Install system packages
# ============================
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    build-essential \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ============================
# Install Node.js 18
# ============================
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get update && apt-get install -y nodejs

# ============================
# Install Walrus CLI (official installer)
# ============================
RUN curl -sSf https://walrus.sh/install.sh | sh
ENV PATH="/root/.walrus/bin:${PATH}"

# ============================
# Install Sui CLI using suiup
# ============================
RUN curl -fsSL https://raw.githubusercontent.com/MystenLabs/suiup/main/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
RUN suiup install sui@testnet

# ============================
# Working directory
# ============================
WORKDIR /app

# ============================
# Copy app source
# ============================
COPY . /app

# ============================
# Install Node deps for Seal
# ============================
RUN cd backend/services && \
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
