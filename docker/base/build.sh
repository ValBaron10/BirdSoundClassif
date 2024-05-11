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

# Copy src files to the build context
cp -r ../../src ./src
cp ../../setup.py ./setup.py

# Build the Docker image with the folder name as the tag and the provided Docker Hub account name
docker build -t "${DOCKER_ACCOUNT}/bird-sound-classif:${FOLDER_NAME}" -f "Dockerfile.${FOLDER_NAME}" .

# Cleanup: Remove copied files
rm -rf ./src
rm ./setup.py
