import xml.etree.ElementTree as ET
from tilespec import TileSpec,Transform,AffineModel,ReferenceTransform
from renderapi import Render
import os
import json
import argparse
import subprocess
import pathos.multiprocessing as mp
from functools import partial

def process_section(z,renderObj=None):
    #get the first tilespec
    post_ts = render.get_tile_specs_from_z(a.postalignedStack, z)[0]
    origts  = render.get_tile_spec(a.prealignedStack, post_ts.tileId)

    #make a list of transform objects for its transforms, this takes this tile from raw space to aligned space
    tform_W_to_A = post_ts.tforms

    #print 'origts',origts.tforms
    #invert the original transformations (assumes they are Affine)
    tform_W_to_R = origts.tforms
    tform_R_to_W = list(tform_W_to_R)
    tform_R_to_W.reverse()
    tform_R_to_W = [tf.invert() for tf in tform_R_to_W]
    
    #print 'tform_R_to_W',tform_R_to_W
    #create a transform list that takes you from registered space to aligned space
    #this can now be appended to all the transforms in the original input stack
    #that share the same Z
    tform_R_to_A = tform_R_to_W + tform_W_to_A
    
    #create a reference transform json, this might be more efficent in the future
    tfd = {}
    tfd['id'] = '%s_to_%s_z_%f_alignment'%(a.prealignedStack,a.postalignedStack,z)
    tfd['type'] = 'list'
    tfd['specList'] = [tf.to_dict() for tf in tform_R_to_A]
    transformFileOut = os.path.join(a.jsonDirectory,
        '%s_to_%s_z_%d_alignment.json'%(a.prealignedStack,a.postalignedStack,z))
    json.dump([tfd],open(transformFileOut,'w'),indent=4)

    
    #collect all the tilespecs
    totts=[]
    original_tilespecs=render.get_tile_specs_from_z(a.inputStack,z)
    for ts in original_tilespecs:
        ts.tforms+=[ReferenceTransform(refId=tfd['id'])]    
        totts.append(ts)
    #dump them to a file and collect the filepaths
    tilespecFileOut = os.path.join(a.jsonDirectory,
        '%s_%s_%s_z_%d_AlignedTilespecs.json'%(a.Owner,a.Project,a.outputStack,z))
    json.dump([ts.to_dict() for ts in totts],open(tilespecFileOut,'w'),indent=4)
    
    return (tilespecFileOut,transformFileOut)


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
    p = argparse.ArgumentParser(description="Takes a TEM2 aligned version of a render stack,\
     and saves this alignment to a new render stack.\n\
     Assumptions: the TEM2 file has tileIds in the oid field of each Patch\n\
     \t the prealignedStack has only affine transformations for each Patch\n\
     \t the renderHome points to a standard render installation where it can find\
     a jdk in ./deploy/jdk* and the converter in a jar in \
     ./render-app/target/render-app*jar-with-dependencies.jar \
     and the import_json script in ./render-ws-java-client/src/main/scripts/ ")
    p.add_argument('--prealignedStack',help='name of render stack used to create TEM2 alignment',required=True)
    p.add_argument('--postalignedStack',           help="Name of TEM2 file with alignment",required=True)
    p.add_argument('--Owner',          help="name of render project owner stacks should exist in",default = DEFAULT_OWNER)
    p.add_argument('--Project',        help="name of render project stacks should exist in",required=True)
    p.add_argument('--jsonDirectory',         help='directory to store json outputs',default='.')
    p.add_argument('--inputStack',           help="name of stack to apply alignment stack", required=True)
    p.add_argument('--outputStack',         help='name of output stack to save alignment to',required=True)
    p.add_argument('--host',                help="host name of the render server",default=DEFAULT_RENDER_HOST)
    p.add_argument('--port',                help="port for render server",default=DEFAULT_RENDER_PORT)
    p.add_argument('--renderHome',           help="directory to find render installation",default=DEFAULT_RENDER_HOME)
    p.add_argument('--verbose',             help="verbose output",action='store_true')
    p.add_argument('--poolSize',            help='number of parallel z sections to process', default=20)

    a = p.parse_args()

    client_scripts = os.path.join(a.renderHome,'render-ws-java-client','src','main','scripts')

    if not os.path.isdir(a.jsonDirectory):
        os.makedirs(a.jsonDirectory)
    #STEP 1: use render service to look up tilespec for the first tile in each layer
    # in the prealignedStack.  Inverts this tiles transform, and applies TEM2 tranform.
    # assumes this creates a transform that can be applied to all tiles in that layer.
    # generally true for TEM2 projects now. The logic is as follows
    # prealignedStack: t1_z0>prealigned_space_z0 via T1, t2_z0>prealigned_space_z0 via T2, etc etc.
    # TEMproject: t1_z0>aligned_space_z0 via T3, t2_z0>aligned_space_z0, etc
    # prealigned_space_z0>aligned_space_z0 is therefore done through T3(T1inverse)
    # output these transforms as a transform file json in json Directory
    # Then use the render service to pull down tilespecs in the inputStack by zvalue
    # alter the tilespecs to append the transform that describes how that z should be modified

    #create a new render connection
    render = Render(a.host,a.port,a.Owner,a.Project,client_scripts)

    zvalues = render.get_z_values_for_stack(a.postalignedStack)
    
    print 'processing %d sections'%len(zvalues)
    #SETUP a processing pool to process each section
    pool =mp.ProcessingPool(a.poolSize)

    #define a partial function that takes in a single z
    partial_process = partial(process_section,renderObj=render)
    partial_process(0)
    #parallel process all sections
    res = pool.amap(partial_process,zvalues)
    
    #wait for results to finish and collect the resulting json file paths
    res.wait()
    results = res.get()
    ztransform_files=[zt for jsonfile,zt in results]
    final_json_files=[jsonfile for jsonfile,zt in results]

    #step 3
    #upload the altered tilespecs and the tranform tilespec to render under the outputStack

    #write out the tilespecs to disk
    #tilespecFileOut = os.path.join(a.jsonDirectory,'%s_%s_%s_AlignedTilespecs.json'%(a.Owner,a.Project,a.outputStack))
    #json.dump([ts.to_dict() for ts in finaltilespecs],open(tilespecFileOut,'w'),indent=4)

    #upload them to render using parallel upload
    render.create_stack(a.outputStack)
    render.import_jsonfiles_and_transforms_parallel_by_z(a.outputStack,final_json_files,ztransform_files,poolsize=a.poolSize,verbose=a.verbose)
