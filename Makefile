.PHONY: taskmates
taskmates:
	poetry run hypercorn --bind 0.0.0.0:55000 taskmates.server.server:app

.PHONY: format
format:
	black .
	isort .

.PHONY: docker-build
docker-build:
	DOCKER_BUILDKIT=1 docker build -f Dockerfile -t taskmates --progress=plain .

.PHONY: docker-run
docker-run:
	docker run -p 55000:55000 taskmates $(filter-out $@,$(MAKECMDGOALS))

.PHONY: devcontainer-build
devcontainer-build:
	mkdir -p tmp/cache/poetry
	DOCKER_BUILDKIT=1 docker buildx build \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--cache-from type=local,src=tmp/cache/poetry \
		--cache-to type=local,dest=tmp/cache/poetry \
		-f .devcontainer/Dockerfile \
		-t devcontainer \
		--progress=plain \
		.

.PHONY: devcontainer-run
devcontainer-run:
	docker run --rm -it devcontainer $(CMD)
