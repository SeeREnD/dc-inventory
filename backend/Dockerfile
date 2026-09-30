# 国内网络不通 Docker Hub 时，可通过 build arg 指定镜像源，如 docker.m.daocloud.io/library
ARG REGISTRY=docker.io/library
FROM ${REGISTRY}/python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV DATABASE_URL=sqlite:////app/data/dc_inventory.db
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
