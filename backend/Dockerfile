######################### BASE IMAGE ############################
FROM python:3.10-slim

######################### SYSTEM DEPS ###########################
RUN apt-get update && apt-get install -y \
    curl git jq xz-utils pkg-config libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

######################### NODE 18 INSTALL ########################
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

RUN node -v && npm -v

######################### INSTALL WALRUS CLI #####################
# Official supported Walrus CLI (JavaScript version)
RUN npm install -g @walrus/cli

# Debug
RUN echo "=== Walrus CLI Installed ===" \
    && walrus --version || echo "Walrus CLI check failed"

######################### INSTALL SUI CLI ########################
ENV SUI_VERSION=testnet-v1.61.1

RUN curl -L "https://github.com/MystenLabs/sui/releases/download/${SUI_VERSION}/sui-${SUI_VERSION}-ubuntu-x86_64.tgz" \
    -o sui.tgz \
    && tar -xzf sui.tgz \
    && SUI_DIR=$(tar -tf sui.tgz | head -n 1 | cut -d/ -f1) \
    && mv "$SUI_DIR/sui" /usr/local/bin/sui \
    && chmod +x /usr/local/bin/sui \
    && rm -rf sui.tgz "$SUI_DIR"

# Debug
RUN echo "=== Sui CLI Installed ===" \
    && sui --version

######################### COPY APP ###############################
WORKDIR /app
COPY . /app

RUN echo "=== Project Structure ===" && ls -R /app

######################## NODE BACKEND ############################
WORKDIR /app/node-backend
RUN npm init -y
RUN npm install @mysten/sui @mysten/seal

######################## WALRUS UPLOADER FIX #####################
RUN if [ -d "/app/walrus-uploader" ]; then \
      echo '{"type":"module"}' > /app/walrus-uploader/package.json; \
      echo "ESM enabled for walrus-uploader"; \
    else \
      echo "walrus-uploader not found (skipping)"; \
    fi

######################## PYTHON DEPENDENCIES #####################
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

######################## START SERVER ############################
ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
