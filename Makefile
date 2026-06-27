.PHONY: setup run install test clean seed

setup:
	python -m venv .venv
	.venv\Scripts\activate && pip install -e .

install:
	.venv\Scripts\activate && pip install -e .

run:
	.venv\Scripts\activate && python scripts/run_pipeline.py --mode daily_news

run-short:
	.venv\Scripts\activate && python scripts/run_shorts.py

seed:
	.venv\Scripts\activate && python scripts/seed_sources.py

test:
	.venv\Scripts\activate && python -m pytest tests/ -v

clean:
 Remove-Item -Recurse -Force __pycache__,.pytest_cache -ErrorAction Silently Continue
	Remove-Item -Force *.pyc -Recurse -ErrorAction Silently Continue

schedule:
	.venv\Scripts\activate && python scripts/scheduler.py

analytics:
	.venv\Scripts\activate && python scripts/collect_analytics.py
