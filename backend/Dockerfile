######################### BASE IMAGE ############################
FROM python:3.10-slim

######################### SYSTEM DEPS ###########################
RUN apt-get update && apt-get install -y \
    curl git jq xz-utils pkg-config libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

######################### NODE 18 INSTALL ########################
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

RUN node -v && npm -v

######################### INSTALL SUI CLI ############################
ENV SUI_VERSION=testnet-v1.61.2

RUN set -eux; \
    curl -L "https://github.com/MystenLabs/sui/releases/download/${SUI_VERSION}/sui-${SUI_VERSION}-ubuntu-x86_64.tgz" -o /tmp/sui.tgz; \
    mkdir -p /tmp/sui-extract; \
    tar -xzf /tmp/sui.tgz -C /tmp/sui-extract; \
    SUI_BIN="$(find /tmp/sui-extract -type f -name sui -print -quit)"; \
    if [ -z "$SUI_BIN" ]; then echo "ERROR: sui binary not found in archive" >&2; exit 1; fi; \
    mv "$SUI_BIN" /usr/local/bin/sui; \
    chmod +x /usr/local/bin/sui; \
    rm -rf /tmp/sui.tgz /tmp/sui-extract; \
    echo "Installed Sui CLI:"; sui --version

######################### SUI WALLET COPY ############################
RUN mkdir -p /app/.sui/sui_config

COPY sui_config/client.yaml /app/.sui/sui_config/client.yaml
COPY sui_config/sui.aliases /app/.sui/sui_config/sui.aliases
COPY sui_config/sui.keystore /app/.sui/sui_config/sui.keystore

RUN chmod 600 /app/.sui/sui_config/sui.keystore
RUN chmod 644 /app/.sui/sui_config/client.yaml
RUN chmod 644 /app/.sui/sui_config/sui.aliases

ENV SUI_CONFIG_DIR=/app/.sui/sui_config
ENV SUI_CLIENT_CONFIG_DIR=/app/.sui/sui_config


RUN echo "=== CHECK SUI WALLET IN CONTAINER ===" && ls -la /app/.sui/sui_config


######################### COPY APP ###############################
WORKDIR /app
COPY . /app

RUN echo "=== Project Structure ===" && ls -R /app

######################## NODE BACKEND ############################
WORKDIR /app
RUN npm install
RUN npm install @mysten/seal
# ❌ REMOVE: Walrus CLI / WASM SDK (not needed)
# RUN npm install @mysten/walrus @mysten/walrus-wasm
# ❌ REMOVE old mysten walrus libs
# --------------------------------------

# ✅ ADD: Node Fetch (required for REST uploader)
RUN npm install node-fetch

RUN npm install dotenv
ENV NODE_PATH=/app/node_modules

######################## WALRUS UPLOADER FIX #####################
RUN if [ -d "/app/walrus-uploader" ]; then \
      echo '{"type":"module"}' > /app/walrus-uploader/package.json; \
      echo "ESM enabled for walrus-uploader"; \
    else \
      echo "walrus-uploader not found (skipping)"; \
    fi

######################## PYTHON DEPENDENCIES #####################
WORKDIR /app

# Build tools are still needed (you said not to remove)
RUN apt-get update && apt-get install -y \
    build-essential gcc g++ cargo rustc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

######################## START SERVER ############################
ENV PORT=10000
EXPOSE 10000
WORKDIR /app
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","10000","--limit-max-requests","100000000"]


