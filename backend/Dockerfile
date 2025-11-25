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
# Install Sui CLI (prebuilt, no GitHub API)
# ----------------------------------------------------
ENV SUI_VERSION=testnet-v1.61.1

RUN curl -L "https://github.com/MystenLabs/sui/releases/download/${SUI_VERSION}/sui-${SUI_VERSION}-ubuntu-x86_64.tgz" \
    -o sui.tgz \
    && tar -xzf sui.tgz \
    && SUI_DIR=$(tar -tf sui.tgz | head -1 | cut -d/ -f1) \
    && mv "$SUI_DIR/sui" /usr/local/bin/sui \
    && chmod +x /usr/local/bin/sui \
    && rm -rf sui.tgz "$SUI_DIR"

# ----------------------------------------------------
# Install Walrus CLI (stable, non-GitHub URL)
# ----------------------------------------------------
RUN curl -L "https://walrus-assets.s3.amazonaws.com/cli/walrus-linux-x64" \
     -o /usr/local/bin/walrus \
    && chmod +x /usr/local/bin/walrus

# ----------------------------------------------------
# App source
# ----------------------------------------------------
WORKDIR /app
COPY . /app

# ----------------------------------------------------
# Node dependencies
# ----------------------------------------------------
RUN npm init -y && npm install @mysten/sui @mysten/seal

RUN if [ -d "walrus-uploader" ]; then \
      cd walrus-uploader && echo '{ "type": "module" }' > package.json; \
    fi

# ----------------------------------------------------
# Python dependencies
# ----------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------
# Environment
# ----------------------------------------------------
ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
