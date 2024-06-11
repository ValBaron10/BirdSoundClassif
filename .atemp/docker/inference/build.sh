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

# Build the Docker image with the folder name as the tag
docker build -t "matthieujln/bird-sound-classif:${FOLDER_NAME}" -f "Dockerfile.${FOLDER_NAME}" .

# Cleanup: Remove copied directories
rm -rf ./app_utils
rm -rf ./model_serve
rm -rf ./inference
rm -rf ./models

