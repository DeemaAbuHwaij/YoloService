FROM python:3.10-slim

# Use a non-conflicting directory
WORKDIR /code

# Install torch-related dependencies first
COPY torch-requirements.txt .
RUN pip install --no-cache-dir -r torch-requirements.txt

# Install app-specific requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire project
COPY . .

EXPOSE 8080

# Run uvicorn from app.py (your FastAPI file)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
