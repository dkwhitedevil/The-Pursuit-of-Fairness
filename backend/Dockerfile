FROM python:3.10-slim

# ============================
# System packages
# ============================
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ============================
# Global Walrus CLI
# ============================
RUN npm install -g @walrus/cli

# ============================
# App source
# ============================
WORKDIR /app
COPY . /app

# ============================
# Seal + Sui SDK (Node)
# ============================
RUN npm install @mysten/sui @mysten/seal

# ============================
# Walrus uploader ESM support
# ============================
# Add a minimal package.json to support "type: module"
RUN if [ -d "walrus-uploader" ]; then \
      cd walrus-uploader && \
      echo '{ "type": "module" }' > package.json; \
    fi

# No npm install needed — upload.js uses only built-in modules

# ============================
# Python dependencies
# ============================
RUN pip install --no-cache-dir -r requirements.txt

# ============================
# Expose API
# ============================
ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
