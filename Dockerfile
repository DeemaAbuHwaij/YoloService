FROM python:3.10

WORKDIR /app

# ✅ Install OpenCV + system dependencies to avoid libGL.so.1 errors
RUN apt-get update && apt-get install -y \
    libgl1 \
    libegl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ✅ Copy your full app source code into /app
COPY . .

# ✅ Install Python dependencies
# First install torch-related deps
RUN pip install --no-cache-dir -r torch-requirements.txt

# Then install the rest of your app deps
RUN pip install --no-cache-dir -r requirements.txt

# ✅ OPTIONAL: Avoid OpenCV GUI dependencies by using headless version
RUN pip uninstall -y opencv-python && pip install opencv-python-headless

# ✅ Expose FastAPI port
EXPOSE 8000

# ✅ Launch app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]