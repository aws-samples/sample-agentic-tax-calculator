FROM python:3.11-slim AS base

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY mcp_server.py .

# Expose MCP server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Use opentelemetry-instrument for auto-instrumentation (ADOT)
# Set DISABLE_ADOT_OBSERVABILITY=true to skip in local dev
CMD ["opentelemetry-instrument", "python", "mcp_server.py"]
