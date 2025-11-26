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
ENV SUI_VERSION=testnet-v1.61.1

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


######################### COPY APP ###############################
WORKDIR /app
COPY . /app

RUN echo "=== Project Structure ===" && ls -R /app
######################## NODE BACKEND ############################
WORKDIR /app
RUN npm install          # installs sui + walrus + dotenv
RUN npm install @mysten/seal   # installs seal
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

# Install build tools for pysui-fastcrypto
RUN apt-get update && apt-get install -y \
    build-essential gcc g++ cargo rustc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

######################## START SERVER ############################
ENV PORT=10000
EXPOSE 10000
WORKDIR /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
