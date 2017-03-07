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
    p = argparse.ArgumentParser(description="Takes a TEM2 aligned version of a render stack,\
     and saves this alignment to a new render stack.\n\
     Assumptions: the TEM2 file has tileIds in the oid field of each Patch\n\
     \t the prealignedStack has only affine transformations for each Patch\n\
     \t the renderHome points to a standard render installation where it can find\
     a jdk in ./deploy/jdk* and the converter in a jar in \
     ./render-app/target/render-app*jar-with-dependencies.jar \
     and the import_json script in ./render-ws-java-client/src/main/scripts/ ")
    p.add_argument('--TEM2file',           help="Name of TEM2 file with alignment",required=True)
    p.add_argument('--Owner',          help="name of render project owner stacks should exist in",default = DEFAULT_OWNER)
    p.add_argument('--Project',        help="name of render project stacks should exist in",required=True)
    p.add_argument('--prealignedStack',help='name of render stack used to create TEM2 alignment',required=True)
    p.add_argument('--jsonDirectory',         help='directory to store json outputs',default='.')
    p.add_argument('--inputStack',           help="name of stack to apply alignment stack (will default to prealigned stack)", default=None)
    p.add_argument('--outputStack',         help='name of output stack to save alignment to',required=True)
    p.add_argument('--host',                help="host name of the render server",default=DEFAULT_RENDER_HOST)
    p.add_argument('--port',                help="port for render server",default=DEFAULT_RENDER_PORT)
    p.add_argument('--renderHome',           help="directory to find render installation",default=DEFAULT_RENDER_HOME)
    p.add_argument('--verbose',             help="verbose output",action='store_true')
    a = p.parse_args()

    #PRESTEPS
    #if no inputStack is specified, assume inputStack=prealignedStack
    
    if a.inputStack is None:
        a.inputStack=a.prealignedStack

    #STEP 1: convert TEM2 file to json files using render Converter 
    #assumes that you have placed the tileId of each tile in the oid field of the TEM2 project
    my_env = os.environ.copy()
    
    #write down the path to the java jdk and make it the JAVA_HOME
    jdk = [os.path.join(a.renderHome,'deploy',f) for f in os.listdir(os.path.join(a.renderHome,'deploy')) if f.startswith('jdk')][0]
    my_env['JAVA_HOME']=jdk

    #write down the location to save the converted tilespec
    TEM2base = os.path.split(a.TEM2file)[1][:-4]

    json_out = os.path.join(a.jsonDirectory,'%s_%s_%s_postAlignment.json'%(a.Owner,a.Project,a.prealignedStack))
    if not os.path.isdir(a.jsonDirectory):
        os.makedirs(a.jsonDirectory)

    #write down the path to the render-app jar with the Converter
    render_app_dir = os.path.join(a.renderHome,'render-app','target')
    converter_jar = [os.path.join(render_app_dir,f) for f in os.listdir(render_app_dir) if ((f.endswith('jar')) \
        and ('jar-with-dependencies' in f))][0]
    
    #run the converter
    cmd = [os.path.join(jdk,'bin','java'),'-cp',converter_jar,'org.janelia.alignment.trakem2.Converter',a.TEM2file,os.path.split(a.TEM2file)[0],json_out]
    proc = subprocess.Popen(cmd,env=my_env)
    proc.wait()

    client_scripts = os.path.join(a.renderHome,'render-ws-java-client','src','main','scripts')

    #STEP 2: use render service to look up tilespec for the first tile in each layer
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
    #read in the json created in step 1
    tem2json = json.load(open(json_out,'r'))

    zvalues = render.get_z_values_for_stack(a.inputStack)
    finaltilespecs =[]
    ztransforms=[]
    
    for z in zvalues:
        #get the first tilespec from the trackem2 file
        tem2ts=[ts for ts in tem2json if ts['z']==z][0]
        #print z,tem2ts['tileId']

        #make a list of transform objects for its transforms, this takes this tile from raw space to aligned space
        tform_W_to_A = [Transform(json=tf) for tf in tem2ts['transforms']['specList']]

        #pull down the tilespecs for this z from render
        origts=render.get_tile_spec(a.prealignedStack,tem2ts['tileId'])
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
        tfd['id'] = '%s_to_%s_z_%f_alignment'%(a.prealignedStack,a.outputStack,z)
        tfd['type'] = 'list'
        tfd['specList'] = [tf.to_dict() for tf in tform_R_to_A]
        ztransforms.append(tfd)
        
        original_tilespecs=render.get_tile_specs_from_z(a.inputStack,z)
        for ts in original_tilespecs:
            ts.tforms+=[ReferenceTransform(refId=tfd['id'])]    
            finaltilespecs.append(ts)

    #step 3
    #upload the altered tilespecs and the tranform tilespec to render under the outputStack

    #write out the transforms to disk
    transformFileOut = os.path.join(a.jsonDirectory,'%s_%s_%s_to_%s_Transforms.json'%(a.Owner,a.Project,a.prealignedStack,a.outputStack))
    json.dump(ztransforms,open(transformFileOut,'w'),indent=4)

    #write out the tilespecs to disk
    tilespecFileOut = os.path.join(a.jsonDirectory,'%s_%s_%s_AlignedTilespecs.json'%(a.Owner,a.Project,a.outputStack))
    json.dump([ts.to_dict() for ts in finaltilespecs],open(tilespecFileOut,'w'),indent=4)

    #upload them to render
    render.create_stack(a.outputStack)
    render.import_jsonfiles(a.outputStack,[tilespecFileOut],transformFile=transformFileOut,verbose=a.verbose)
