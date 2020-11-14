FROM python:3.7
WORKDIR /
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
COPY requirements.txt requirements.txt
RUN apt update
RUN apt-get install -y libsndfile1
RUN apt-get install -y ffmpeg
RUN pip install -r requirements.txt
EXPOSE 5000
COPY static static
COPY templates templates
COPY app.py app.py
COPY utils.py utils.py
RUN apt-get install -y fluidsynth

CMD ["flask", "run"]
