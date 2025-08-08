FROM python:3.13-slim

WORKDIR /code

RUN pip install --no-cache-dir --upgrade poetry

COPY pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

COPY ./backend.py ./index.html /code/

ENV AKTIVISTI_USERNAME=<email>
ENV AKTIVISTI_PASSWORD=<password>

CMD ["fastapi", "run", "backend.py", "--port", "8000"]
