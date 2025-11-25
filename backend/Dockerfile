# ============================
# BASE IMAGE
# ============================
FROM python:3.10-slim

# ============================
# Install Node.js (required for walrus + seal)
# ============================
RUN apt-get update && apt-get install -y curl gnupg build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    node -v && npm -v

# ============================
# Set working directory
# ============================
WORKDIR /app

# ============================
# Copy backend files
# ============================
COPY . /app

# ============================
# Install Python dependencies
# ============================
RUN pip install --no-cache-dir -r requirements.txt

# ============================
# Expose port (Render uses $PORT)
# ============================
ENV PORT=10000

EXPOSE 10000

# ============================
# Start FastAPI using Uvicorn
# ============================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
