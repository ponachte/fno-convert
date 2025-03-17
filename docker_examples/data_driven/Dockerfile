FROM ubuntu:20.04

# install Python and Python requirements
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
COPY requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt

# copy all job files to home directory & give execution rights
WORKDIR /home
COPY job/. .
RUN find . -type f -exec chmod 0744 {} \;

# run the command on container startup
ENTRYPOINT [ "python3", "run.py" ]