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

# Ensure the destination directory exists
mkdir -p ./api
# Copy the contents of the source api directory to the already created destination directory
cp -r ../../app/api/. ./api/
echo "Checking the '/api' content brought to image build context:"
ls ./api

# Build the Docker image with the folder name as the tag and the provided Docker Hub account name
docker build -t "${DOCKER_ACCOUNT}/bird-sound-classif:${FOLDER_NAME}" -f "Dockerfile.${FOLDER_NAME}" --build-arg BASE_IMAGE="${DOCKER_ACCOUNT}/bird-sound-classif:base" .

# Cleanup: Remove copied directories
rm -rf ./app_utils
rm -rf ./api
