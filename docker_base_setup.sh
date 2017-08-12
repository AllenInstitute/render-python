docker pull atbigdawg:5000/fcollman/render:latest
docker tag atbigdawg:5000/fcollman/render:latest fcollman/render:latest
docker build -t fcollman/render-python-base:latest -f Dockerfile.base .
docker tag fcollman/render-python-base:latest atbigdawg:5000/fcollman/render-python-base:latest
docker push atbigdawg:5000/fcollman/render-python-base:latest
