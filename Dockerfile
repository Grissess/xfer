FROM fundanie/hypercorn:latest

COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8080
ENTRYPOINT [ "hypercorn", "-b", "0.0.0.0:8080", "./xfer:app" ]
