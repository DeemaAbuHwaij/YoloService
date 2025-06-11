FROM python:3.10

WORKDIR /app

# Install OpenCV runtime dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ./app .

RUN pip install --no-cache-dir -r torch-requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

RUN pip uninstall opencv-python -y && \
    pip install opencv-python-headless

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
