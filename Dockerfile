FROM python:3.12-slim

WORKDIR /app

# Install dependencies from packages/pyproject.toml
COPY packages/pyproject.toml packages/pyproject.toml
RUN pip install --no-cache-dir ./packages

# Copy full repo (imports use packages.* paths)
COPY . .

EXPOSE 8080

CMD ["uvicorn", "packages.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
