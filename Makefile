clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

lint:
	uv tool run ruff check --fix

format:
	uv tool run ruff format
