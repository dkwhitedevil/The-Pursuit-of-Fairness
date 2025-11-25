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
# Global Walrus CLI (UPDATED)
# ============================
# Force correct version so "walrus store" works
RUN npm install -g @walrus/cli@latest

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
RUN if [ -d "walrus-uploader" ]; then \
      cd walrus-uploader && \
      echo '{ "type": "module" }' > package.json; \
    fi

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
