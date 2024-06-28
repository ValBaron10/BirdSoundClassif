#!/bin/bash
SCRIPT_DIR=$(dirname "$0")

cd "$SCRIPT_DIR"

# Get the name of the containing folder
FOLDER_NAME=$(basename "$PWD")

# Get the Docker Hub account name from the command line argument
DOCKER_ACCOUNT=$1

# Check if the Docker Hub account name is provided
if [ -z "$DOCKER_ACCOUNT" ]; then
    echo "Please provide a Docker Hub account name as an argument."
    exit 1
fi

# Ensure the app_utils directory exists
mkdir -p ./app_utils
# Copy the contents of the app_utils directory to the already created destination directory
cp -r ../../app/app_utils/. ./app_utils/
ls ./app_utils

# Ensure the model_serve directory exists
mkdir -p ./model_serve
# Copy the contents of the model_serve directory to the already created destination directory
cp -r ../../app/model_serve/. ./model_serve/
ls ./model_serve

# Ensure the destination directory exists
mkdir -p ./inference
# Copy the contents of the source inference directory to the already created destination directory
cp -r ../../app/inference/. ./inference/

# Copy model weights to the build context
ls ../../models/
mkdir -p ./models
cp -r ../../models/detr_noneg_100q_bs20_r50dc5 ./models/detr_noneg_100q_bs20_r50dc5

# Build the Docker image with the folder name as the tag and the provided Docker Hub account name
docker build -t "${DOCKER_ACCOUNT}/bird-sound-classif:${FOLDER_NAME}" -f "Dockerfile.${FOLDER_NAME}" --build-arg BASE_IMAGE="${DOCKER_ACCOUNT}/bird-sound-classif:base" .

# Cleanup: Remove copied directories
rm -rf ./app_utils
rm -rf ./model_serve
rm -rf ./inference
rm -rf ./models
