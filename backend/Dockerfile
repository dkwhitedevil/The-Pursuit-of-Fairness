############## STAGE 1: Build Walrus ################
FROM rust:1.75-slim AS walrus-builder

RUN apt-get update && apt-get install -y pkg-config libssl-dev curl

WORKDIR /build

# Download Walrus source tarball
RUN curl -L https://github.com/MystenLabs/walrus/archive/refs/heads/main.tar.gz -o walrus.tar.gz \
    && tar -xzf walrus.tar.gz \
    && rm walrus.tar.gz

# Enter the CLI crate
WORKDIR /build/walrus-main/walrus-cli

# Build Walrus CLI
RUN cargo build --release


############## STAGE 2: Build Final App ##############
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    curl git jq xz-utils pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node 18+
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Copy Walrus CLI from builder
COPY --from=walrus-builder /build/walrus-main/walrus-cli/target/release/walrus /usr/local/bin/walrus
RUN chmod +x /usr/local/bin/walrus

# Install Sui CLI
ENV SUI_VERSION=testnet-v1.61.1
RUN curl -L "https://github.com/MystenLabs/sui/releases/download/${SUI_VERSION}/sui-${SUI_VERSION}-ubuntu-x86_64.tgz" \
    -o sui.tgz \
    && tar -xzf sui.tgz \
    && SUI_DIR=$(tar -tf sui.tgz | head -n 1 | cut -d/ -f1) \
    && mv "$SUI_DIR/sui" /usr/local/bin/sui \
    && chmod +x /usr/local/bin/sui \
    && rm -rf sui.tgz "$SUI_DIR"

# App source
WORKDIR /app
COPY . /app

# Node modules in separate folder
WORKDIR /app/node-backend
RUN npm init -y && npm install @mysten/sui @mysten/seal

# Enable ESM in walrus-uploader if exists
RUN if [ -d "/app/walrus-uploader" ]; then \
      cd /app/walrus-uploader && echo '{"type":"module"}' > package.json; \
    fi

# Python deps
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
