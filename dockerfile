# 1. Use an official Python runtime as a parent image
FROM python:3.13-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the application code into the container
COPY . .

# 4. Install in editable mode
RUN pip install --no-cache-dir -e .

# 5. Set the Python path so bare imports resolve from src/
ENV PYTHONPATH=/app/src:/app

# 6. Make port 8080 available to the world outside this container
EXPOSE 8080

# 7. Run the application with uvicorn
CMD ["uvicorn", "infrastructure.web.app:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/app/src"]