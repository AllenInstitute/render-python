<<<<<<< Updated upstream
FROM continuumio/anaconda
=======
FROM fcollman/render
>>>>>>> Stashed changes
MAINTAINER Forrest Collman (forrest.collman@gmail.com)

#install java
# auto validate license
RUN echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections
RUN echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee /etc/apt/sources.list.d/webupd8team-java.list
RUN echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee -a /etc/apt/sources.list.d/webupd8team-java.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EEA14886
RUN apt-get update
RUN apt-get install oracle-java8-installer -y
ENV JAVA_HOME /usr/lib/jvm/java-8-oracle

#install pathos,multiprocess with gcc
RUN apt-get install gcc -y
RUN apt-get install build-essential -y
RUN apt-get clean
RUN pip install multiprocess
RUN pip install pathos

#install components for common render-python apps
#jupyter notebook, shapely with geos
RUN /opt/conda/bin/conda install jupyter -y
RUN apt-get install libgeos-dev -y
RUN pip install shapely==1.6b2

#install render python using pip from github
#RUN pip install -e git+https://github.com/fcollman/render-python.git@master#egg=render-python

RUN pip install coverage==4.1 \
mock==2.0.0 \
pep8==1.7.0 \
pytest==3.0.5 \
pytest-cov==2.2.1 \
pytest-pep8==1.0.6 \
pytest-xdist==1.14 \
flake8>=3.0.4 \
pylint>=1.5.4
RUN mkdir -p /usr/local/render-python
COPY . /usr/local/render-python
WORKDIR /usr/local/render-python
RUN python setup.py install

ENTRYPOINT [ "/usr/bin/tini", "--" ]
CMD [ "/bin/bash" ]
