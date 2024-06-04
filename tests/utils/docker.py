import os
import time
from python_on_whales import docker

def is_container_ready(container):
    container.reload()
    return container.state.running

def wait_for_stable_status(container, stable_duration=3, interval=1):
    start_time = time.time()
    stable_count = 0
    while time.time() - start_time < stable_duration:
        if is_container_ready(container):
            stable_count += 1
        else:
            stable_count = 0

        if stable_count >= stable_duration / interval:
            return True

        time.sleep(interval)

    return False

def create_internal_network():
    if "internal" not in [network.name for network in docker.network.list()]:
        docker.network.create("internal")

def start_inference_container():
    create_internal_network()
    container = docker.run(
        image=os.getenv("DOCKERHUB_USERNAME") + "/bird-sound-classif:inference",
        detach=True,
        envs={
            "RABBITMQ_HOST": "rabbitmq",
            "RABBITMQ_PORT": "5672",
            "MINIO_ENDPOINT": "minioserver:9000",
            "MINIO_BUCKET": "minio-bucket-name",
            "AWS_ACCESS_KEY_ID": "minio-access-key",
            "AWS_SECRET_ACCESS_KEY": "minio-secret-key",
        },
        networks=["internal"],
        command=["sh", "-c", "sleep 5 && python3 inference/main.py"]
    )
    if wait_for_stable_status(container):
        return container
    else:
        raise RuntimeError("Inference container did not start properly")