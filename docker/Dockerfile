# Mission server as a container:  docker build -f docker/Dockerfile -t water-bomber . && docker run -p 8000:8000 -e BOMBER_SEED=1 water-bomber
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "mcp>=1.12" uvicorn
COPY bomber /app/bomber
EXPOSE 8000
CMD ["python", "-m", "bomber.mcp_server", "--transport", "http", "--port", "8000"]
