# render-python

This is a python API setup to interact via python with render databases and facilitate python scripting of tilespec creation
see
https://github.com/saalfeldlab/render
it presently interacts with render via a web-api, though a couple functions are presently implemented with the java client scripts that are part of render, ideally those would be cutout.

tilespec.py is a set of python objects that facilitate serializing and deserializing objects to/from json.

[add_downsample_to_render_project.py](docs/examples/add_downsample_to_render_project.py) is an example script that makes use of these files to read tilespecs from a render stack,
modify the tilespecs to include paths to downsampled images, and then write those tilespecs to disk, upload them back to render, and launch all the jobs to create those downsampled images in a parallel fashion.  This program assumes a filestructure path that is unique to the Synapse Biology group at the Allen Institute, but nonetheless demonstrate the general utility of the above files.

[create_mipmaps.py](docs/examples/create_mipmaps.py) is a simple python program for using Pillow to create downsampled images from a single image that is included simply for reference.

Render connection objects created with `renderapi.connect()` can default to environment variables.  Below is an example of the variables which can be sourced and added to ~/.bashrc or ~/.bash_profile.
```
    export RENDER_HOST="localhost"
    export RENDER_PORT="8080"
    export RENDER_PROJECT="YOURPROJECT"
    export RENDER_OWNER="YOURNAME"
    export RENDER_CLIENT_SCRIPTS=".../render/render-ws-java-client/src/main/scripts"
    export RENDER_CLIENT_SCRIPT="$RENDER_CLIENT_SCRIPTS/run_ws_client.sh"
    export RENDER_CLIENT_HEAP="1G"
```

[Usage examples for an Array Tomography workflow](https://github.com/fcollman/render-python-apps/tree/newrender) are available.
