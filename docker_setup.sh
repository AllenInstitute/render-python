docker pull atbigdawg:5000/fcollman/render
docker tag atbigdawg:5000/fcollman/render fcollman/render
docker build -t fcollman/render-python .
docker tag fcollman/render-python atbigdawg:5000/fcollman/render-python
docker push atbigdawg:5000/fcollman/render-python
