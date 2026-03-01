.PHONY: install test dev clean

install:
	pip install -r requirements.txt

test:
	python -m pytest

dev:
	# Start Celery worker with concurrency of 4
	celery -A celery_app worker --loglevel=info -c 4

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
