#!/bin/sh

# Starting MinIO server
minio server /data --console-address ':9001' &

# Delay to ensure MinIO server starts up
sleep 3

# Setting up MinIO client alias for admin
mc alias set myminio http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Creating bucket
mc mb myminio/${MINIO_BUCKET}

# Adding non-admin user and setting permissions
mc admin user add myminio ${AWS_ACCESS_KEY_ID} ${AWS_SECRET_ACCESS_KEY}

# Ensure the policy exists and then attach it
mc admin policy add myminio readwrite /etc/minio/policies/readwrite.json
mc admin policy attach myminio readwrite --user ${AWS_ACCESS_KEY_ID}

# Keeping the container running
tail -f /dev/null
