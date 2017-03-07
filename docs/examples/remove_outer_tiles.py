from tilespec import TileSpec,Transform,AffineModel,ResolvedTileSpecCollection, ResolvedTileSpecMap
from renderapi import Render
import os
import json
import numpy as np
from rtree import index as rindex
import networkx as nx
import argparse

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
    p = argparse.ArgumentParser(description="Detect stitching mistakes in a render project\
    and save a new stack with dropped tiles. Takes a pre-stitched stack, and a post-stitched stack\
    as well as name of a stack to save the resulting version with dropped tiles")
    p.add_argument('--Owner',          help="name of render project owner stacks should exist in",default = DEFAULT_OWNER)
    p.add_argument('--Project',        help="name of render project stacks should exist in",required=True)
    p.add_argument('--inputStack',     help='name of render stack to remove tiles',required=True)
    p.add_argument('--jsonDirectory',         help='directory to store json outputs',default='.')
    p.add_argument('--outputStack',         help='name of output stack to save alignment to',required=True)
    p.add_argument('--host',                help="host name of the render server",default=DEFAULT_RENDER_HOST)
    p.add_argument('--port',                help="port for render server",default=DEFAULT_RENDER_PORT)
    p.add_argument('--renderHome',           help="directory to find render installation",default=DEFAULT_RENDER_HOME)
    p.add_argument('--verbose',             help="verbose output",action='store_true',default=False)
    p.add_argument('--edge_threshold',      help='distance between tilespecs to consider as edges', default = 1843)
    a = p.parse_args()
    #STEP1: setup render connection
    client_scripts = os.path.join(a.renderHome,'render-ws-java-client','src','main','scripts')
    render = Render(a.host,a.port,a.Owner,a.Project,default_client_scripts=client_scripts)

    #STEP 2: get z values of input stack
    zvalues=render.get_z_values_for_stack(a.inputStack)

    #STEP 3: loop over z values
    jsonfiles = []
    for z in zvalues:
        #setup an Rtree to find overlapping tiles
        ridx = rindex.Index()
        #setup a graph to store overlapping tiles
        G=nx.Graph()
        Gpos = {}
        #get all the tilespecs for this z 
        tilespecs = render.get_tile_specs_from_z(a.inputStack,z)
        #insert them into the Rtree with their bounding boxes to assist in finding overlaps
        #label them by order in pre_tilespecs
        [ridx.insert(i,(ts.minX,ts.minY,ts.maxX,ts.maxY)) for i,ts in enumerate(tilespecs)]

        #loop over each tile in this z
        for i,ts in enumerate(tilespecs):

            #get the list of overlapping nodes
            nodes=list(ridx.intersection((ts.minX,ts.minY,ts.maxX,ts.maxY)))
            #remove itself
            nodes.remove(i)


            for node in nodes:
                dpre=tilespecs[node].tforms[0].M[0:2,3]-tilespecs[i].tforms[0].M[0:2,3]
                dp = np.sqrt(np.sum(dpre**2))
                #add these nodes to the undirected graph
                if (dp<2048*.9):
                    G.add_edge(i,node)
            Gpos[i]=((ts.minX+ts.maxX)/2,(ts.minY+ts.maxY)/2)

        #find the non-central nodes
        nodes_to_remove = []
        for node in G.nodes_iter():
            if len(G.neighbors(node))<4:
                nodes_to_remove.append(node)
        #remove them
        [G.remove_node(node) for node in nodes_to_remove]

        #create new json files that include the
        ts_good_json = [tilespecs[node].to_dict() for node in G.nodes_iter()]
        jsonfilepath = os.path.join(a.jsonDirectory,'%s_z%04.0f.json'%(a.outputStack,z))
        json.dump(ts_good_json,open(jsonfilepath ,'w'))
        jsonfiles.append(jsonfilepath)


    #create stack and upload to render
    render.create_stack(a.outputStack)
    render.import_jsonfiles(a.outputStack,jsonfiles,verbose=a.verbose)

    
  


