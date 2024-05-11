.PHONY: build-base build-api build-inference build-all run-api run-inference run-all
#===================================#
# 		BUILD DOCKER IMAGES			#
#===================================#
build-base:
	cd docker/base && ./build.sh

build-api:
	cd docker/api && ./build.sh

build-inference:
	cd docker/inference && ./build.sh

build-all: build-base build-api build-inference


#===================================#
# 		PUSH DOCKER IMAGES			#
#===================================#
# Default dockerhub account
DOCKER_ACCOUNT ?= matthieujln

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
# 			DOCKER COMPOSE			#
#===================================#
run-api:
	docker compose up api

run-inference:
	docker compose up inference

run-all:
	docker compose up

shutdown:
	docker compose down

teardown:
	docker compose down -v


#===================================#
# 			DEV COMMANDS			#
#===================================#
upload-dev:
	curl -X 'GET' \
	'http://localhost:8001/upload-dev?email=user%40example.com' \
	-H 'accept: application/json'
