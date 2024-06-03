# Use the base image for the API service
FROM ubuntu:jammy-20240416

# Enable terminal color support
RUN echo 'export TERM=xterm-256color' >> /etc/profile

WORKDIR /app

# Install Python 3.10 and dependencies
RUN apt-get update \
    && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get install -y python3.10 python3-pip

# Install additional tools and dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && apt-get clean

RUN echo "alias python='python3'" >> /root/.bashrc

# Set the working directory
WORKDIR /workspace