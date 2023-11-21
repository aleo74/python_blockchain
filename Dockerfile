FROM python:3.10

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install .

EXPOSE 50001

CMD ["run", "-ip", "127.0.0.1", "-p", "50001"]