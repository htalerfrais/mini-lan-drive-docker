#!/bin/bash

IMAGE_NAME="lan-drive"
CONTAINER_NAME="lan-drive-container"

docker volume create lan-drive-data

echo "▶ Removing existing container (if any)..."
docker rm -f $CONTAINER_NAME >/dev/null 2>&1

echo "▶ Building image..."
docker build -t $IMAGE_NAME .

echo "▶ Running container..."
docker run \
  --name $CONTAINER_NAME \
  -p 8080:8080 \
  -v lan-drive-data:/data \
  $IMAGE_NAME