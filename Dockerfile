FROM python:3
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt

COPY update_team.py /code/update_team.py
COPY main.py /code/main.py 

WORKDIR /code/