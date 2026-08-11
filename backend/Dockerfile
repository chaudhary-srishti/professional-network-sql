FROM python:3.12-slim

WORKDIR /srv

# Install the app + its runtime dependencies from pyproject (setuptools build backend).
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8000

# DATABASE_URL is provided by docker-compose (points at the db service).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
