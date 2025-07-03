FROM python:3.13

WORKDIR /code

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app ./app

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]