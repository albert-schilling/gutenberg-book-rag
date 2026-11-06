.PHONY: app reports eval test lint screenshots

app:  ## the chat app
	uv run streamlit run streamlit_app.py

reports:  ## the dashboard of the evaluation reports
	uv run streamlit run streamlit_reports.py

eval:  ## evaluate the default book (calls the language model)
	uv run book-rag-eval

test:  ## unit tests; add -m browser for the browser tests
	uv run pytest -m "not browser and not live and not integration"

lint:
	uv run ruff check . && uv run ruff format --check .

screenshots:  ## the pictures of the README
	uv run python scripts/take_screenshots.py
