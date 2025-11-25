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
# Install suiup (official installer)
# ----------------------------------------------------
RUN curl -sSfL https://raw.githubusercontent.com/Mystenlabs/suiup/main/install.sh | sh

# Add Sui & Walrus binaries to PATH
ENV PATH="/root/.sui/bin:/root/.cargo/bin:${PATH}"

# ----------------------------------------------------
# Install Sui & Walrus CLI (non-interactive)
# ----------------------------------------------------
RUN suiup install sui
RUN suiup install walrus

# ----------------------------------------------------
# App source
# ----------------------------------------------------
WORKDIR /app
COPY . /app

# ----------------------------------------------------
# Node dependencies for backend
# ----------------------------------------------------
RUN npm init -y && npm install @mysten/sui @mysten/seal

# If ESM uploader folder exists, convert to module mode
RUN if [ -d "walrus-uploader" ]; then \
      cd walrus-uploader && \
      echo '{ "type": "module" }' > package.json; \
    fi

# ----------------------------------------------------
# Python dependencies
# ----------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------
# Environment + Port
# ----------------------------------------------------
ENV PORT=10000
EXPOSE 10000

# ----------------------------------------------------
# Start FastAPI / Uvicorn
# ----------------------------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
