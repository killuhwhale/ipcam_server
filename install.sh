#!/usr/bin/bash

# Install docker


DL_LINK="https://desktop.docker.com/linux/main/amd64/docker-desktop-4.10.1-amd64.deb?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-linux-amd64"

curl -s $DL_LINK --output docker.deb
echo "Installing Docker for Linux."

sudo dpkg -i  studio.deb

echo "Done downloading and installing Docker"

sudo rm studio.deb

