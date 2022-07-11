.. image:: https://readthedocs.org/projects/render-python/badge/
   :target: http://render-python.readthedocs.io/en/latest/
   :alt: Documentation Status 
.. image:: https://travis-ci.com/AllenInstitute/render-python.svg?branch=master
   :target: https://travis-ci.com/AllenInstitute/render-python
   :alt: Build Status
.. image:: https://codecov.io/gh/AllenInstitute/render-python/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/AllenInstitute/render-python
  
render-python
#############

This is a python API client to interact with `render <https://github.com/saalfeldlab/render>`_ and facilitate python scripting of `tilespec <https://github.com/saalfeldlab/render/blob/master/docs/src/site/markdown/data-model.md>`_ creation

it presently interacts with render via a web-api, though the `client module <renderapi/client.py>`_ aims to interface by calling java client scripts to avoid server-side processing.

Render connection objects created with `renderapi.connect()` can default to environment variables.  Below is an example of the variables which can be sourced and added to, e.g.,  ~/.bashrc or ~/.bash_profile.
::

    export RENDER_HOST="localhost"
    export RENDER_PORT="8080"
    export RENDER_PROJECT="YOURPROJECT"
    export RENDER_OWNER="YOURNAME"
    export RENDER_CLIENT_SCRIPTS=".../render/render-ws-java-client/src/main/scripts"
    export RENDER_CLIENT_SCRIPT="$RENDER_CLIENT_SCRIPTS/run_ws_client.sh"
    export RENDER_CLIENT_HEAP="1G"


`Usage examples for a development Array Tomography workflow <https://github.com/fcollman/render-python-apps>`_ are available.

Documentation 
#############
http://render-python.readthedocs.io/en/latest/

Government Sponsorship
######################
Supported by the Intelligence Advanced Research Projects Activity (IARPA) via Department of Interior / Interior Business Center (DoI/IBC) contract number D16PC00004. The U.S. Government is authorized to reproduce and distribute reprints for Governmental purposes notwithstanding any copyright annotation thereon. Disclaimer: The views and conclusions contained herein are those of the authors and should not be interpreted as necessarily representing the official policies or endorsements, either expressed or implied, of IARPA, DoI/IBC, or the U.S. Government.

.. _render :
