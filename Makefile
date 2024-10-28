.PHONY: taskmates
taskmates:
	poetry run hypercorn --bind 0.0.0.0:55000 taskmates.server.server:app

.PHONY: format
format:
	black .
	isort .


docker-build:
	DOCKER_BUILDKIT=1 docker build -f Dockerfile -t taskmates --progress=plain .

docker-run:
	docker run -p 55000:55000 taskmates
