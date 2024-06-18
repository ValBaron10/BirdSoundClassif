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

docker login

docker push "${DOCKER_ACCOUNT}/bird-sound-classif:${FOLDER_NAME}"