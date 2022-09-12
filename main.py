'''
Install docker and run the two images...

docker images list
docker tag espcam_esp32server:latest killuhwhale/camserver_api:latest
docker tag espcam_frontend:latest killuhwhale/camserver:latest
docker push killuhwhale/camserver:latest
docker push killuhwhale/camserver_api:latest


docker tag local-image:tagname new-repo:tagname
docker push new-repo:tagname
'''

import argparse
from typing import List
import docker
from docker import DockerClient
from docker.models.images import Image
import subprocess


client: DockerClient = docker.from_env()
# client.containers.run("ubuntu:latest", "echo hello world")


def start():
    print("Starting")
    print("Starting")
    # Install docker on CPU
    # Pip install docker
    # Once docker is installed
    # Run script with docker to run image

    images: List[Image] = client.images.list(name="killuhwhale")
    for img in images:
        print(img.tags)

    print("Pulling")
    client.images.pull("killuhwhale/camserver:latest")
    client.images.pull("killuhwhale/camserver_api:latest")

    dc = subprocess.run(["docker-compose", "up", "-d"],
                        capture_output=True, universal_newlines=True)

    print(dc.stdout)
    print(dc.stderr)


def stop():
    print("Stopping")
    dc = subprocess.run(["docker-compose", "down"],
                        capture_output=True, universal_newlines=True)

    print(dc.stdout)
    print(dc.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="iCamServer Docker/ compose required.")
    parser.add_argument("-s", "--start", action="store_true",
                        help="Start iCamServer.")
    parser.add_argument("-q", "--quit", action="store_true",
                        help="Quit iCamServer.")
    args = parser.parse_args()
    if args.start:
        start()

    if args.quit:
        stop()
