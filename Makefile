run:
	uvicorn server:app --host 0.0.0.0 --port 8001 --reload

run_with_midi:
	MIDI_DEVICE='IAC Driver Bus 1' uvicorn server:app --host 0.0.0.0 --port 8001 --reload

lint:
	python3 -m isort --force-single-line-imports musictools tests
	python3 -m flake8 --ignore E221,E501,W503,E701,E704,E741,I100,I201 musictools tests

test:
	python3 -m pytest -v --cov=musictools tests

coverage_report:
	python3 -m pytest -v --cov=musictools --cov-report=html tests
	open htmlcov/index.html

clean_docker:
	docker rmi musictools

run_docker:
	docker build -t musictools .
	docker run --name musictools -d --rm -p 8001:8001 musictools

daw:
	python3.9 -m musictools.daw
