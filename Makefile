.PHONY: build-base build-api build-inference build-all run-api run-inference run-all


# Default dockerhub account
DOCKER_ACCOUNT ?= matthieujln

#===================================#
#       ENV VARIABLES
#===================================#
generate-dotenv:
	cp .env.example .env


#===================================#
#       TRAINED PT MODEL
#===================================#

FILE_URL=https://www.dropbox.com/scl/fi/gx8mal2itlricdbhni75b/detr_noneg_100q_bs20_r50dc5.tar?rlkey=xv44e8bw6bbmj2gveif448gio&st=uz5uf4v0&dl=1
FILE_NAME=detr_noneg_100q_bs20_r50dc5.tar
TARGET_DIR=models
ARCHIVE_DIR=detr_noneg_100q_bs20_r50dc5

download-model:
	@echo "Downloading file from Dropbox..."
	@wget -O $(FILE_NAME) '$(FILE_URL)'
	@echo "Extracting the archive..."
	@mkdir -p $(TARGET_DIR)/$(ARCHIVE_DIR)
	@tar -xf $(FILE_NAME) -C $(TARGET_DIR)/$(ARCHIVE_DIR)
	@rm $(FILE_NAME)
	@echo "Download and extraction complete."


#===================================#
#       BUILD DOCKER IMAGES
#===================================#
build-base:
	cd docker/base && ./build.sh $(DOCKER_ACCOUNT)

build-api:
	cd docker/api && ./build.sh $(DOCKER_ACCOUNT)

build-inference:
	cd docker/inference && ./build.sh $(DOCKER_ACCOUNT)

build-all:
	$(MAKE) build-base
	$(MAKE) build-api
	$(MAKE) build-inference


#===================================#
#        PUSH DOCKER IMAGES
#===================================#
push-base:
	cd docker/base && ./push.sh $(DOCKER_ACCOUNT)

push-api:
	cd docker/api && ./push.sh $(DOCKER_ACCOUNT)

push-inference:
	cd docker/inference && ./push.sh $(DOCKER_ACCOUNT)

push-all:
	$(MAKE) push-base
	$(MAKE) push-api
	$(MAKE) push-inference


#===================================#
#       DOCKER COMPOSE
#===================================#

# Network name
NETWORK_NAME=external_network

# Create the network if it doesn't exist
create-network:
	@if [ -z "$(shell docker network ls --filter name=^$(NETWORK_NAME)$$ --format='{{ .Name }}')" ]; then \
		echo "Creating network $(NETWORK_NAME)"; \
		docker network create $(NETWORK_NAME); \
	else \
		echo "Network $(NETWORK_NAME) already exists"; \
	fi

run-api:
	DOCKERHUB_USERNAME=$(DOCKER_ACCOUNT) docker compose up api

run-inference:
	DOCKERHUB_USERNAME=$(DOCKER_ACCOUNT) docker compose up inference

run-all: create-network
	DOCKERHUB_USERNAME=$(DOCKER_ACCOUNT) docker compose up

shutdown:
	docker compose down

teardown:
	docker compose down -v



#===================================#
#           CI TOOLS
#===================================#
install-ci-tools:
	pip install -r requirements_ci.txt


format:
	ruff format .

lint:
	ruff check --fix .

run-pre-commit:
	pre-commit run --all-files
	pre-commit run --all-files

#===================================#
#       DEV COMMANDS
#===================================#
upload-dev:
	curl -X 'GET' \
	'http://localhost:8001/upload-dev?email=user%40example.com' \
	-H 'accept: application/json'
