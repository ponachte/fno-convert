FROM ubuntu:20.04

# install Python and Python requirements
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

# copy all job files to home directory & give execution rights
WORKDIR /home
COPY . .
RUN find . -type f -exec chmod 0744 {} \;

# run the command on container startup
ENTRYPOINT [ "python3", "run.py" ]