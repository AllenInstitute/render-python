docker pull atbigdawg:5000/fcollman/render-python-base:latest
docker tag atbigdawg:5000/fcollman/render-python-base:latest fcollman/render-python-base:latest
docker build -t fcollman/render-python:latest .
docker tag fcollman/render-python:latest atbigdawg:5000/fcollman/render-python:latest
docker push atbigdawg:5000/fcollman/render-python:latest
