# 1. Use an official Python runtime as a parent image
FROM python:3.13-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Install dependencies first (cached unless pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . 2>/dev/null || pip install --no-cache-dir .

# 4. Copy only the source code
COPY src/ ./src/

# 5. Install in editable mode with source present
RUN pip install --no-cache-dir -e .

# 6. Set the Python path so bare imports resolve from src/
ENV PYTHONPATH=/app/src:/app

# 7. Make port 8080 available to the world outside this container
EXPOSE 8080

# 8. Run the application with uvicorn
CMD ["uvicorn", "infrastructure.web.app:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/app/src"]