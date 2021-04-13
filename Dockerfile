FROM tiangolo/uvicorn-gunicorn:python3.8

LABEL maintainer="xdream oldlu <xdream@gmail.com>"

COPY ./app /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt