FROM python:3.10-slim

# =============================
# System Packages
# =============================
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# =============================
# Install Sui CLI (Testnet)
# =============================
RUN curl -fsSL https://github.com/MystenLabs/sui/releases/download/testnet-release/sui-linux-x86_64 \
    -o /usr/local/bin/sui && \
    chmod +x /usr/local/bin/sui

# Verify Sui installed
RUN sui --version

# =============================
# Install Walrus CLI globally
# =============================
RUN npm install -g @walrus/cli

# =============================
# App Source
# =============================
WORKDIR /app
COPY . /app

# =============================
# Seal + Sui SDK (Node)
# =============================
RUN npm install @mysten/sui @mysten/seal

# =============================
# Walrus uploader ESM support
# =============================
RUN if [ -d "walrus-uploader" ]; then \
      cd walrus-uploader && \
      echo '{ "type": "module" }' > package.json; \
    fi

# =============================
# Python Dependencies
# =============================
RUN pip install --no-cache-dir -r requirements.txt

# =============================
# Expose API
# =============================
ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
