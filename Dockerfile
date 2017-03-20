FROM fcollman/render
MAINTAINER Forrest Collman (forrest.collman@gmail.com)

#install anaconda
RUN apt-get update --fix-missing && apt-get install -y wget bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1 \
    git mercurial subversion

RUN apt-get install -y curl grep sed dpkg && \
    TINI_VERSION=`curl https://github.com/krallin/tini/releases/latest | grep -o "/v.*\"" | sed 's:^..\(.*\).$:\1:'` && \
    curl -L "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini_${TINI_VERSION}.deb" > tini.deb && \
    dpkg -i tini.deb && \
    rm tini.deb

RUN echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/conda.sh && \
wget --quiet https://repo.continuum.io/archive/Anaconda2-4.3.1-Linux-x86_64.sh -O ~/anaconda.sh && \
/bin/bash ~/anaconda.sh -b -p /opt/conda && \
rm ~/anaconda.sh

ENV PATH /opt/conda/bin:$PATH

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
RUN apt-get clean

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
