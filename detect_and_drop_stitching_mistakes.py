from tilespec import TileSpec,Transform,AffineModel,ResolvedTileSpecCollection, ResolvedTileSpecMap
from renderapi import Render
import os
import json
import numpy as np
from rtree import index as rindex
import networkx as nx
import argparse
import pathos.multiprocessing as mp
from functools import partial

DEFAULT_DISTANCE_THRESHOLD = 50
DEFAULT_EDGE_THRESHOLD = 1843

def process_section(z,
    renderObj=None,
    prestitchedStack='',
    poststitchedStack='',
    outputStack='',
    distance_threshold=DEFAULT_DISTANCE_THRESHOLD,
    edge_threshold=DEFAULT_EDGE_THRESHOLD):

    ridx = rindex.Index() #setup an Rtree to find overlapping tiles
    G=nx.Graph() #setup a graph to store overlapping tiles
    Gpos = {} #dictionary to store positions of tiles
    
    #get all the tilespecs for this z from prestitched stack
    pre_tilespecs = render.get_tile_specs_from_z(prestitchedStack,z)
    #insert them into the Rtree with their bounding boxes to assist in finding overlaps
    #label them by order in pre_tilespecs
    [ridx.insert(i,(ts.minX,ts.minY,ts.maxX,ts.maxY)) for i,ts in enumerate(pre_tilespecs)]
    
    post_tilespecs = []
    #loop over each tile in this z to make graph
    for i,ts in enumerate(pre_tilespecs):
        #create the list of corresponding post stitched tilespecs
        post_tilespecs.append(render.get_tile_spec(poststitchedStack,ts.tileId))
        
        #get the list of overlapping nodes
        nodes=list(ridx.intersection((ts.minX,ts.minY,ts.maxX,ts.maxY)))
        nodes.remove(i) #remove itself
        [G.add_edge(i,node) for node in nodes] #add these nodes to the undirected graph
        
        #save the tiles position
        Gpos[i]=((ts.minX+ts.maxX)/2,(ts.minY+ts.maxY)/2)
        
    #loop over edges in the graph
    for p,q in G.edges():
        #p and q are now indices into the tilespecs, and labels on the graph nodes
        
        #assuming the first transform is the right one, and is only translation
        #this is the vector between these two tilespecs
        dpre=pre_tilespecs[p].tforms[0].M[0:2,3]-pre_tilespecs[q].tforms[0].M[0:2,3]
        #this is therefore the distance between them
        dp = np.sqrt(np.sum(dpre**2))
        #this is the vector between them after stitching
        dpost=post_tilespecs[p].tforms[0].M[0:2,3]-post_tilespecs[q].tforms[0].M[0:2,3]
        #this is the amplitude of the vector between the pre and post vectors (delta delta vector)
        delt = np.sqrt(np.sum((dpre-dpost)**2))
        #store it in the edge property dictionary
        G[p][q]['distance']=delt
        #if the initial distance was too big, or if the delta delta vector is too large
        if (delt>distance_threshold) | (dp>edge_threshold):
            #remove the edge
            G.remove_edge(p,q)

    #after removing all the bad edges...
    #get the largest connected component of G
    Gc = max(nx.connected_component_subgraphs(G), key=len)
    
    #use it to pick out the good post stitch tilspecs that remain in the graph
    ts_good_json = [post_tilespecs[node].to_dict() for node in Gc.nodes_iter()]
    #formulate a place to save them
    jsonfilepath = os.path.join(a.jsonDirectory,'%s_z%04.0f.json'%(outputStack,z))
    #dump the json to that location
    json.dump(ts_good_json,open(jsonfilepath ,'w'))
    #return the name of the file
    return jsonfilepath

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
    p.add_argument('--prestitchedStack',help='name of render stack of tiles before stitching',required=True)
    p.add_argument('--poststitchedStack',help='name of render stack of tiles before stitching',required=True)
    p.add_argument('--jsonDirectory',         help='directory to store json outputs',default='.')
    p.add_argument('--outputStack',         help='name of output stack to save alignment to',required=True)
    p.add_argument('--host',                help="host name of the render server",default=DEFAULT_RENDER_HOST)
    p.add_argument('--port',                help="port for render server",default=DEFAULT_RENDER_PORT)
    p.add_argument('--renderHome',           help="directory to find render installation",default=DEFAULT_RENDER_HOME)
    p.add_argument('--verbose',             help="verbose output",action='store_true',default=False)
    p.add_argument('--distance_threshold',  help='amplitude difference between pre and post stitching results, that causes edge to be tossed (units of render)', default = DEFAULT_DISTANCE_THRESHOLD)
    p.add_argument('--edge_threshold',      help='distance between tilespecs to consider as edges', default = DEFAULT_EDGE_THRESHOLD)
    p.add_argument('--poolSize',            help='number of parallel z sections to process', default=20)
    a = p.parse_args()
    #STEP1: setup render connection
    client_scripts = os.path.join(a.renderHome,'render-ws-java-client','src','main','scripts')
    render = Render(a.host,a.port,a.Owner,a.Project,default_client_scripts=client_scripts)

    if not os.path.isdir(a.jsonDirectory):
        os.makedirs(a.jsonDirectory)

    #STEP 2: get z values of stitched stack
    zvalues=render.get_z_values_for_stack(a.prestitchedStack)
    
    print 'processing %d sections'%len(zvalues)
    #SETUP a processing pool to process each section
    pool =mp.ProcessingPool(a.poolSize)

    #define a partial function that takes in a single z
    partial_process = partial(process_section,renderObj=render,prestitchedStack=a.prestitchedStack,
        poststitchedStack=a.poststitchedStack,outputStack=a.outputStack,
        distance_threshold=a.distance_threshold,edge_threshold=a.edge_threshold)

    #parallel process all sections
    res = pool.amap(partial_process,zvalues)
    
    #wait for results to finish and collect the resulting json file paths
    res.wait()
    jsonfiles = res.get()


    #create stack and upload to render
    render.create_stack(a.outputStack)
    render.import_jsonfiles_parallel(a.outputStack,jsonfiles,verbose=a.verbose)

    
  


