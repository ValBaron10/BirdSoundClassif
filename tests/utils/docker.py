import os
import time

import python_on_whales


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


def start_database_container():
    client = python_on_whales.client.from_env()
    scripts_dir = os.path.abspath("")
