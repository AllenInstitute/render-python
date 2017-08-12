FROM fcollman/render-python-base:latest
MAINTAINER Forrest Collman (forrest.collman@gmail.com)

RUN mkdir -p /usr/local/render-python
COPY . /usr/local/render-python
WORKDIR /usr/local/render-python
RUN python setup.py install

ENTRYPOINT [ "/usr/bin/tini", "--" ]
CMD [ "/bin/bash" ]
