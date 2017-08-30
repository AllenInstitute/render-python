FROM fcollman/render-python-base:latest
MAINTAINER Forrest Collman (forrest.collman@gmail.com)

RUN mkdir -p /shared/render-python
COPY . /shared/render-python
WORKDIR /shared/render-python
RUN python setup.py install

ENTRYPOINT [ "/usr/bin/tini", "--" ]
CMD [ "/bin/bash" ]
