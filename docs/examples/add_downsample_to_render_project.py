import jsonschema
import json
import os
import subprocess
import copy
from tilespec import TileSpec,Layout,AffineModel,ResolvedTileSpecMap,ResolvedTileSpecCollection
import numpy as np
from sh import tar,zip
import renderapi
my_env = os.environ.copy()
import requests
from itertools import izip_longest
import argparse

def make_tilespecs_and_cmds(render,inputStack,outputStack,inputOwner,inputProject,outputProject,outputOwner,tilespecdir):
    zvalues=render.get_z_values_for_stack(inputStack,owner = inputOwner,project = inputProject)
    cmds = []
    tilespecpaths=[]
    for z in zvalues:
        tilespecs = render.get_tile_specs_from_z(inputStack,z,owner=inputOwner,project=inputProject)
        
        for i,tilespec in enumerate(tilespecs):
            
            filepath=str(tilespec.imageUrl).lstrip('file:')
            fileparts=filepath.split(os.path.sep)[1:]
            downdir=os.path.join(os.path.sep,
                              fileparts[0],
                              fileparts[1],
                              fileparts[2],
                              'processed',
                              'downsampled_images',
                              fileparts[5],
                              fileparts[6],
                              fileparts[7])
            #construct command for creating mipmaps for this tilespec
            downcmd = ['python','create_mipmaps.py','--inputImage',filepath,'--outputDirectory',downdir,'--mipmaplevels','1','2','3']
            tilespecdir = os.path.join(os.path.sep,
                                       fileparts[0], 
                                       fileparts[1],
                                       fileparts[2],
                                       'processed',
                                       tilespecdir)
            if not os.path.isdir(tilespecdir):
                os.makedirs(tilespecdir)
            if not os.path.isdir(downdir):
                os.makedirs(downdir)
            cmds.append(downcmd)
            filebase = os.path.split(filepath)[1]
            tilespec.scale1Url = 'file:' + os.path.join(downdir,filebase[0:-4]+'_mip01.jpg')
            tilespec.scale2Url = 'file:' + os.path.join(downdir,filebase[0:-4]+'_mip02.jpg')
            tilespec.scale3Url = 'file:' + os.path.join(downdir,filebase[0:-4]+'_mip03.jpg')
        tilespecpath = os.path.join(tilespecdir,outputProject+'_'+outputOwner+'_'+outputStack+'_%04d.json'%z)
        fp = open(tilespecpath,'w')
        json.dump([ts.to_dict() for ts in tilespecs],fp,indent=4)
        fp.close()
        tilespecpaths.append(tilespecpath)
    return tilespecpaths,cmds
 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Take an existing render stack, and create a new render stack with downsampled tilespecs and create those downsampled tiles")

    parser.add_argument('--renderHost',help="host name of the render server",default="ibs-forrestc-ux1")
    parser.add_argument('--renderPort',help="port of the render server",default = 8080)
    parser.add_argument('--inputOwner',help="name of project owner to read project from",default = "Forrest")
    parser.add_argument('--outputOwner',help="name of project owner to upload edited tilespec with downsamples (Default to same as input)",default = None)
    parser.add_argument('--inputProject',help="name of the input Project",required=True)
    parser.add_argument('--outputProject',help="name of the output Project (Default to same as input)",default=None)
    parser.add_argument('--inputStack',help='name of stack to take in',required=True)
    parser.add_argument('--outputStack',help='name of stack to upload to render',required=True) 
    parser.add_argument('--outputTileSpecDir',help='location to save tilespecs before uploading to render (default to ',default='tilespec_downsampled')
    parser.add_argument('--client_scripts',help='path to render client scripts',default='/pipeline/render/render-ws-java-client/src/main/scripts')
    parser.add_argument('--ndvizBase',help="base url for ndviz surface",default="http://ibs-forrestc-ux1:8000/render/172.17.0.1:8081")
    parser.add_argument('--verbose',help="verbose output",default=False)
    args = parser.parse_args()


    #fill in outputOwner and outputProjet with inputOwner and inputProject if left blank
    if args.outputOwner is None:
        args.outputOwner = args.inputOwner
    if args.outputProject is None:
        args.outputProject = args.inputProject

    render = renderapi.Render(args.renderHost,args.renderPort,args.inputOwner,args.inputProject)
    #create a new stack to upload to render
    render.create_stack(args.outputStack,owner=args.outputOwner,project=args.outputProject,verbose=args.verbose,client_scripts=args.client_scripts)

    #go get the existing input tilespecs, make new tilespecs with downsampled URLS, save them to the tilespecpaths, and make a list of commands to make downsampled images
    tilespecpaths,cmds = make_tilespecs_and_cmds(render,args.inputStack,args.outputStack,args.inputOwner,args.inputProject,args.outputProject,args.outputOwner,args.outputTileSpecDir)

    #upload created tilespecs to render
    render.import_jsonfiles_parallel(args.outputStack,tilespecpaths,owner=args.outputOwner,project=args.outputProject,verbose=args.verbose,client_scripts=args.client_scripts)

    #launch jobs to create downsampled images
    groups = [(subprocess.Popen(cmd, stdout=subprocess.PIPE) for cmd in cmds)] * 48 # itertools' grouper recipe
    for processes in izip_longest(*groups): # run len(processes) == limit at a time
        for p in filter(None, processes):
            p.wait()

    print "finished!"

