FROM python:3.10-slim

# ----------------------------------------------------
# System deps
# ----------------------------------------------------
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    xz-utils \
    pkg-config \
    libssl-dev \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------
# Install Sui (latest linux x86_64)
# Auto-detects REAL URL from GitHub API
# ----------------------------------------------------
RUN LATEST_SUI_URL=$( \
      curl -s https://api.github.com/repos/MystenLabs/sui/releases/latest \
      | jq -r '.assets[] | select(.name | contains("ubuntu-x86_64")).browser_download_url' \
    ) \
    && echo "Downloading Sui from: $LATEST_SUI_URL" \
    && curl -L "$LATEST_SUI_URL" -o sui.tgz \
    && tar -xzf sui.tgz \
    && mv sui-testnet-*/bin/sui /usr/local/bin/sui \
    && chmod +x /usr/local/bin/sui \
    && rm -rf sui.tgz sui-testnet-*

# ----------------------------------------------------
# Install Rust (for Walrus)
# ----------------------------------------------------
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# ----------------------------------------------------
# Install Walrus CLI
# (This is correct — GitHub releases do NOT exist)
# ----------------------------------------------------
RUN cargo install walrus

# ----------------------------------------------------
# Walrus uploader (Node ESM support)
# ----------------------------------------------------
RUN npm install -g @walrus/cli

# ----------------------------------------------------
# App source
# ----------------------------------------------------
WORKDIR /app
COPY . /app

# Node libs used by your backend
RUN npm install @mysten/sui @mysten/seal

# For ESM uploader folder
RUN if [ -d "walrus-uploader" ]; then \
      cd walrus-uploader && \
      echo '{ "type": "module" }' > package.json; \
    fi

# Python deps
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------
# Run API
# ----------------------------------------------------
ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
