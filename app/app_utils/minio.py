"""MinIO Utility Module.

This module provides utility functions for interacting with MinIO object storage. It
includes functions for ensuring bucket existence, writing files to MinIO, and fetching
files from MinIO.

"""

import io
import os

import logging
logging.basicConfig(level=logging.INFO)


def ensure_bucket_exists(minio_client, bucket_name) -> None:
    """
    Ensures that the specified bucket exists in MinIO, creating it if necessary.

    Args:
        minio_client (Minio): MinIO client instance.
        bucket_name (str): Name of the bucket to check or create.
    """
    logging.info(f"Checking if bucket '{bucket_name}' exists...")
    if not minio_client.bucket_exists(bucket_name):
        logging.info(f"Bucket '{bucket_name}' does not exist. Creating bucket...")
        minio_client.make_bucket(bucket_name)
        logging.info(f"Bucket '{bucket_name}' created successfully.")
    else:
        logging.info(f"Bucket '{bucket_name}' already exists.")


def write_file_to_minio(minio_client, bucket_name, file_name, data) -> None:
    """
    Writes a file to MinIO.

    Args:
        minio_client (Minio): MinIO client instance.
        bucket_name (str): Name of the bucket to write the file to.
        file_name (str): Name of the file to be written.
        data (Union[bytes, IOBase]): File data as bytes or a file-like object.
    """
    logging.info(f"Writing file '{file_name}' to MinIO bucket '{bucket_name}'...")
    if isinstance(data, bytes):
        length = len(data)
        data = io.BytesIO(data)
    else:
        length = data.seek(0, os.SEEK_END)
        data.seek(0)

    try:
        minio_client.put_object(bucket_name, file_name, data, length=length)
        logging.info(
            f"File '{file_name}' written to MinIO bucket '{bucket_name}' successfully."
        )
    except Exception as e:
        logging.error(
            f"Error writing file '{file_name}' to MinIO bucket '{bucket_name}': {str(e)}"
        )
        raise


def fetch_file_from_minio(
    minio_client, bucket_name, file_name, local_file_path
) -> bool:
    """
    Fetches a file from MinIO and saves it locally.

    Args:
        minio_client (Minio): MinIO client instance.
        bucket_name (str): Name of the bucket to fetch the file from.
        file_name (str): Name of the file to be fetched.
        local_file_path (str): Local file path to save the fetched file.

    Returns:
        bool: True if the file was fetched successfully, False otherwise.
    """
    logging.info(f"Fetching file '{file_name}' from MinIO bucket '{bucket_name}'...")
    try:
        minio_client.fget_object(bucket_name, file_name, local_file_path)
        logging.info(
            f"File '{file_name}' fetched from MinIO bucket '{bucket_name}' and saved to '{local_file_path}' successfully."
        )
        return True
    except Exception as e:
        logging.error(
            f"Error fetching file '{file_name}' from MinIO bucket '{bucket_name}': {str(e)}"
        )
        return False
