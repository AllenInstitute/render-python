import xml.etree.ElementTree as ET
from tilespec import TileSpec,Transform,AffineModel,ReferenceTransform
from renderapi import Render
import os
import json
import argparse
import subprocess

if __name__ == '__main__':

    #inputfile='/nas/data/M247514_Rorb_1/scripts/test/out_edit2.xml'
    #inputOwner = 'Forrest'
    #inputProject = 'M247514_Rorb_1'
    #inputStack = 'REGFLATDAPI_1'
    #outputStack = 'ALIGNEDDAPI_1'
    #outputDir = '/nas/data/M247514_Rorb_1/processed/aligned_tilespecs'
    #host = 'ibs-forrestc-ux1.corp.alleninstitute.org'
    #port = 8081

    DEFAULT_OWNER = 'Sharmishtaas'
    DEFAULT_RENDER_HOST = 'ibs-forrestc-ux1.corp.alleninstitute.org'   
    DEFAULT_RENDER_PORT = 8080
    DEFAULT_RENDER_HOME = '/pipeline/render/'
    p = argparse.ArgumentParser(description="Applies the transforms by reference to each z slice,\
     from one renderstack to another \n\
     Assumptions: the TEM2 file has tileIds in the oid field of each Patch\n\
     \t the prealignedStack has only affine transformations for each Patch\n\
     \t the renderHome points to a standard render installation where it can find\
     a jdk in ./deploy/jdk* and the converter in a jar in \
     ./render-app/target/render-app*jar-with-dependencies.jar \
     and the import_json script in ./render-ws-java-client/src/main/scripts/ ")
    p.add_argument('--Owner',          help="name of render project owner stacks should exist in",default = DEFAULT_OWNER)
    p.add_argument('--Project',        help="name of render project stacks should exist in",required=True)
    p.add_argument('--prealignedStack',help='name of render stack used to generate alignment (before alignment)',required=True)
    p.add_argument('--postalignedStack',help='name of render stack used to generate alignment (after alignment)',required=True)
    p.add_argument('--jsonDirectory',         help='directory to store/find json outputs',default='.')
    p.add_argument('--inputStack',           help="name of input stack to apply alignment to (before alignment)",required=True)
    p.add_argument('--outputStack',         help='name of output stack to apply alignment to (after alignment)',required=True)
    p.add_argument('--host',                help="host name of the render server",default=DEFAULT_RENDER_HOST)
    p.add_argument('--port',                help="port for render server",default=DEFAULT_RENDER_PORT)
    p.add_argument('--renderHome',           help="directory to find render installation",default=DEFAULT_RENDER_HOME)
    p.add_argument('--verbose',             help="verbose output",default=False,action='store_true')
    a = p.parse_args()

    #STEP 1: read in the tilespecs from the inputStack from render, and append the appropriate reference
    #transform for each z value
    client_scripts = os.path.join(a.renderHome,'render-ws-java-client','src','main','scripts')
    
    #create a new render connection
    render = Render(a.host,a.port,a.Owner,a.Project,client_scripts)

    #query the z values in this stack
    zvalues = render.get_z_values_for_stack(a.postalignedStack)
    finaltilespecs =[]

    for z in zvalues:

        #pull down the tilespecs for this z from render
        transform_refId = '%s_to_%s_z_%f_alignment'%(a.prealignedStack,a.postalignedStack,z)
        original_tilespecs=render.get_tile_specs_from_z(a.inputStack,z)
        for ts in original_tilespecs:
            ts.tforms+=[ReferenceTransform(refId=transform_refId)]    
            finaltilespecs.append(ts)

    #STEP 2
    #upload the altered tilespecs and the tranform tilespec to render under the outputStack

    #write out the tilespecs to disk
    tilespecFileOut = os.path.join(a.jsonDirectory,'%s_%s_%s_AlignedTilespecs.json'%(a.Owner,a.Project,a.inputStack))
    json.dump([ts.to_dict() for ts in finaltilespecs],open(tilespecFileOut,'w'),indent=4)

    transformFileOut = os.path.join(a.jsonDirectory,'%s_%s_%s_to_%s_Transforms.json'%(a.Owner,a.Project,a.prealignedStack,a.postalignedStack))

    #upload them to render
    render.create_stack(a.outputStack)
    render.import_jsonfiles(a.outputStack,[tilespecFileOut],transformFile=transformFileOut,verbose=a.verbose)
