FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# install node deps for seal + walrus uploader
RUN cd services && \
    npm init -y && \
    npm install @mysten/sui @mysten/seal

# install walrus uploader dependencies
RUN cd walrus-uploader && \
    npm init -y && \
    npm install

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=10000
EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
