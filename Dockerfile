FROM continuumio/anaconda
MAINTAINER Forrest Collman (forrest.collman@gmail.com)

#install java
# auto validate license
RUN echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections
# update repos
RUN echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee /etc/apt/sources.list.d/webupd8team-java.list
RUN echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee -a /etc/apt/sources.list.d/webupd8team-java.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EEA14886
RUN apt-get update
RUN apt-get install oracle-java8-installer -y
ENV JAVA_HOME /usr/lib/jvm/java-8-oracle
#install gcc for pathos
RUN apt-get install gcc -y
RUN apt-get clean
RUN pip install multiprocess
RUN pip install pathos
RUN uptime&&uptime&&uptime&&uptime&&uptime
#install render python using pip from github

RUN pip install -e git+https://github.com/fcollman/render-python.git@module#egg=render-python

