FROM python:3.11-slim
WORKDIR /usr/share/app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/  .
RUN useradd -r -u 1001 -g root adapter
USER adapter
CMD ["python", "./rythu-bandhu-get-farmer-crop-data.py"]