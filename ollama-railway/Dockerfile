FROM ollama/ollama:latest

# Pull your model when container builds
RUN ollama pull qwen2.5:0.5b

# Expose Ollama server
EXPOSE 11434

# Start Ollama server
CMD ["serve"]
