#!/bin/bash
SCRIPT_DIR=$(dirname "$0")

cd "$SCRIPT_DIR"

# Get the name of the containing folder
FOLDER_NAME=$(basename "$PWD")

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

# Build the Docker image with the folder name as the tag
docker build -t "matthieujln/bird-sound-classif:${FOLDER_NAME}" -f "Dockerfile.${FOLDER_NAME}" .

# Cleanup: Remove copied directories
rm -rf ./app_utils
rm -rf ./api