
#
# Quick kludge to call the Render serice API for point requests.
#

#
# TODO: Make a nice clean Pythonic API for these & other calls to the renderer.
#


import tempfile
import os
import json
import subprocess
import sys
import requests
import numpy as np
from tilespec import TileSpec,StackVersion
this = sys.modules[__name__]  
from io import BytesIO
import numpy as np
from PIL import Image



# DEFAULT_HOST = "renderer.int.janelia.org"
this.DEFAULT_HOST = "ibs-forrestc-ux1.corp.alleninstitute.org"
this.DEFAULT_PORT = 8080
this.DEFAULT_OWNER = "Forrest"
this.DEFAULT_PROJECT = "M246930_Scnn1a_4"
this.DEFAULT_CLIENT_SCRIPTS = "/pipeline/render/render-ws-java-client/src/main/scripts"

# GET http://{host}:{port}/render-ws/v1/owner/{owner}/project/{project}/stack/{stack}/z/{z}/world-to-local-coordinates/{x},{y}
# curl "http://renderer.int.janelia.org:8080/render-ws/v1/owner/flyTEM/project/fly_pilot/stack/20141107_863/z/2239/world-to-local-coordinates/40000,40000"
# returns:
# [
#   {
#     "tileId": "140422184419060139",
#     "visible": true,
#     "local": [
#       1238.9023,
#       1044.9727,
#       2239.0
#     ]
#   }
# ]
class Render(object):
    DEFAULT_HOST = "ibs-forrestc-ux1.corp.alleninstitute.org"
    DEFAULT_PORT = 8080
    DEFAULT_OWNER = "Forrest"
    DEFAULT_PROJECT = "M246930_Scnn1a_4"
    DEFAULT_CLIENT_SCRIPTS = "/pipeline/render/render-ws-java-client/src/main/scripts"
    
    def __init__(self,default_host,default_port,default_owner,default_project,default_client_scripts=this.DEFAULT_CLIENT_SCRIPTS):
        self.DEFAULT_HOST = default_host
        self.DEFAULT_PORT = default_port
        self.DEFAULT_PROJECT = default_project
        self.DEFAULT_OWNER = default_owner
        self.DEFAULT_CLIENT_SCRIPTS = default_client_scripts

    def process_defaults(self,host,port,owner,project,client_scripts=DEFAULT_CLIENT_SCRIPTS):
        if host is None:
            host=self.DEFAULT_HOST
        if port is None:
            port = self.DEFAULT_PORT
        if owner is None:
            owner = self.DEFAULT_OWNER
        if project is None:
            project = self.DEFAULT_PROJECT
        if client_scripts is None:
            client_scripts = self.DEFAULT_CLIENT_SCRIPTS
        return (host,port,owner,project,client_scripts)

    def make_stack_params(self,host,port,owner,project,stack):
        baseurl = self.format_baseurl(host,port)
        project_params = ['--baseDataUrl', baseurl, '--owner', owner, '--project', project]
        stack_params= project_params + ['--stack', stack]
        return stack_params

    def delete_stack(self,stack,host=None,port=None,owner=None,project=None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)
        r=session.delete(request_url)
        print r.text           
        return r

    def create_stack(self,stack,cycleNumber=1,cycleStepNumber=1,
                    client_scripts = None,host = None,port = None,owner = None,
                    project = None,verbose=False,session=requests.session()):


        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project,client_scripts)
        sv = StackVersion(cycleNumber=cycleNumber,cycleStepNumber=cycleStepNumber)
        request_url = self.format_preamble(host,port,owner,project,stack)
        print "stack version2",request_url,sv.to_dict()
        payload = json.dumps(sv.to_dict())
        r = session.post(request_url,data=payload,headers={"content-type":"application/json","Accept":"application/json"})
        try:
            return r
        except:
            print r.text
            return None

        # import subprocess
        # my_env = os.environ.copy()
        # stack_params = self.make_stack_params(host,port,owner,project,stack)
        # cmd = [os.path.join(client_scripts, 'manage_stacks.sh')] + \
        # stack_params + \
        # ['--action', 'CREATE', '--cycleNumber', '%d'%cycleNumber, '--cycleStepNumber', '%d'%cycleStepNumber]
        # if verbose:
        #     print cmd
        # proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
        # proc.wait()
        # if verbose:
        #     print proc.stdout.read()
            
    def import_jsonfiles(self,stack,jsonfiles,transformFile = None,
                         client_scripts=DEFAULT_CLIENT_SCRIPTS,host = None,port = None,
                         owner = None,project = None,verbose=False):
        (host,port,owner,project,client_scripts)=\
        self.process_defaults(host,port,owner,project,client_scripts)

        self.set_stack_state(stack,'LOADING',host,port,owner,project)
      
        if transformFile is None:
            transform_params = []
        else:
            transform_params = ['--transformFile',transformFile]
        import subprocess
        my_env = os.environ.copy()
        stack_params = self.make_stack_params(host,port,owner,project,stack)
        cmd = [os.path.join(client_scripts, 'import_json.sh')] + \
        stack_params + \
        transform_params + \
        jsonfiles
        if verbose:
            print cmd
        proc = subprocess.Popen(cmd, env=my_env, stdout=subprocess.PIPE)
        proc.wait()
        if verbose:
            print proc.stdout.read()
        self.set_stack_state(stack,'COMPLETE',host,port,owner,project)
        
            
    def world_to_local_coordinates(self,stack, z, x, y, host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)

        request_url = self.format_preamble(host,port,owner,project,stack)+"/z/%d/world-to-local-coordinates/%f,%f" % (z, x, y)

        r = session.get(request_url)
        try:
            #print(r.json())
            return r.json()
        except:
            print(r.text)
            return None

    # GET http://{host}:{port}/render-ws/v1/owner/{owner}/project/{project}/stack/{stack}/tile/{tileId}/local-to-world-coordinates/{x},{y}
    # curl "http://renderer.int.janelia.org:8080/render-ws/v1/owner/flyTEM/project/fly_pilot/stack/20141107_863/tile/140422184419063136/local-to-world-coordinates/1244.0508,1433.8711"
    # returns:
    # {
    #   "tileId": "140422184419063136",
    #   "world": [
    #     40000.0,
    #     40000.004,
    #     2239.0
    #   ]
    # }
    def local_to_world_coordinates(self,stack, tileId, x, y, host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)

        request_url = self.format_preamble(host,port,owner,project,stack)+"/tile/%s/local-to-world-coordinates/%f,%f" % (tileId, x, y)

        r = session.get(request_url)
        try:
            #print(r.json())
            return r.json()
        except:
            print(r.text)
            return None

    def get_owners(self,host=None,port=None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,None,None)
        request_url =  "%s/owners/"%self.format_baseurl(host,port)
        return self.process_simple_url_request(request_url,session)

    def get_projects_by_owner(self,owner=None,host=None,port=None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,None)
        metadata = self.get_stack_metadata_by_owner(owner)
        projects = list(set([m['stackId']['project'] for m in metadata]))
        return projects

    def get_stacks_by_owner_project(self,owner=None,project=None,host=None,port=None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        metadata = self.get_stack_metadata_by_owner(owner)
        stacks =([m['stackId']['stack'] for m in metadata if m['stackId']['project']==project])
        return stacks

    def get_stack_metadata_by_owner(self,owner=None,host=None,port=None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,None)
        request_url =  "%s/owner/%s/stacks/"%(self.format_baseurl(host,port),owner)
        print request_url
        return self.process_simple_url_request(request_url,session)

    # PUT http://{host}:{port}/render-ws/v1/owner/{owner}/project/{project}/stack/{stack}/z/{z}/local-to-world-coordinates
    # with request body containing JSON array of local coordinate elements
    # curl -H "Content-Type: application/json" -X PUT --data @coordinate-local.json "http://renderer.int.janelia.org:8080/render-ws/v1/owner/flyTEM/project/fly_pilot/stack/20141107_863/z/2239/local-to-world-coordinates" 
    # [
    #   {
    #     "tileId": "140422184419063136",
    #     "world": [
    #       40000.0,
    #       40000.004,
    #       2239.0
    #     ]
    #   }
    # ]
    def world_to_local_coordinates_batch(self,stack, z, data, host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/z/%d/world-to-local-coordinates" % (z)
        r = session.put(request_url, data=data, headers={"content-type":"application/json"})


        #print r.text
        return r.json()

    # curl -H "Content-Type: application/json" -X PUT --data @coordinate-world.json "http://renderer.int.janelia.org:8080/render-ws/v1/owner/flyTEM/project/fly_pilot/stack/20141107_863/z/2239/world-to-local-coordinates" 
    # [
    #   [
    #     {
    #       "tileId": "140422184419060139",
    #       "visible": true,
    #       "local": [
    #         1238.9023,
    #         1044.9727,
    #         2239.0
    #       ]
    #     }
    #   ]
    # ]
    def get_z_values_for_stack(self,stack,project = None,
    host = None,port = None,owner = None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/zValues/"
        print request_url
        r = session.get(request_url)
        try:
            return r.json()
        except:
            print(r.text)
            return None
        
    def get_z_value_for_section(self,stack,sectionId,project = None,
    host = None,port = None,owner = None,session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/section/%s/z"%(sectionId)
        r = session.get(request_url)
        try:
            #print(r.json())
            return r.json()
        except:
            print(r.text)
            return None                        
    def get_tile_image_data(self,stack,tileId,host=None,port=None,owner=None,project=None,session=requests.session(),verbose=False):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/tile/%s/png-image" % (tileId)
        if verbose:
            print request_url
        r = session.get(request_url)
        try:
            img = Image.open(BytesIO(r.content))
            array = np.asarray(img)
            return array
        except:
            print (r.text)    
            return None

    def world_to_local_coordinates_array(self,stack, dataarray, tileId, z=0,host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/z/%d/world-to-local-coordinates" % (z)
        dlist =[]
        for i in range(dataarray.shape[0]):
            d ={}
            d['tileId']=tileId
            d['world']=[dataarray[i,0],dataarray[i,1]]
            dlist.append(d)
        jsondata=json.dumps(dlist)
        
        r = session.put(request_url, data=jsondata, headers={"content-type":"application/json"})

        json_answer = r.json()
        #print json_answer
        try:
            answer = np.zeros(dataarray.shape)

            for i,coord in enumerate(json_answer):

                c = coord['local']
                answer[i,0]=c[0]
                answer[i,1]=c[1]
            return answer

        except:
            print json_answer
            return None
        
    def local_to_world_coordinates_array(self,stack, dataarray, tileId, z=0,host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/z/%d/local-to-world-coordinates" % (z)
        dlist =[]
        for i in range(dataarray.shape[0]):
            d ={}
            d['tileId']=tileId
            d['local']=[dataarray[i,0],dataarray[i,1]]
            dlist.append(d)
        jsondata=json.dumps(dlist)
        
        r = session.put(request_url, data=jsondata, headers={"content-type":"application/json"})

        json_answer = r.json()
        #print json_answer
        try:
            answer = np.zeros(dataarray.shape)

            for i,coord in enumerate(json_answer):

                c = coord['world']
                answer[i,0]=c[0]
                answer[i,1]=c[1]
            return answer

        except:
            print json_answer
            return None

                                        
    def local_to_world_coordinates_batch(self,stack, data, z, host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/z/%d/local-to-world-coordinates" % (z)
        
        
        r = session.put(request_url, data=data, headers={"content-type":"application/json"})

        #print r.text()
        return r.json()

    def format_baseurl(self,host,port):
        return 'http://%s:%d/render-ws/v1'%(host,port)

    def format_preamble(self,host,port,owner,project,stack):
        preamble = "%s/owner/%s/project/%s/stack/%s"%(self.format_baseurl(host,port),owner,project,stack)
        return preamble

    def process_simple_url_request(self,request_url,session):
        r = session.get(request_url)
        try:
            #print(r.json())
            return r.json()
        except:
            #print e
            print(r.text)
            return None
    def put_resolved_tilespecs(self,stack,data,host = None,port = None,owner = None,project = None,
                               session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/resolvedTiles"
        print 'new',request_url
        
        r = session.put(request_url, data=data, headers={"content-type":"application/json","Accept":"text/plain"})
        return r

        
    # http://renderer.int.janelia.org:8080/render-ws/v1/owner/flyTEM/project/fly_pilot/stack/20141107_863/tile/140422184419060139
    def get_tile_spec(self,stack, tile, host = None, port = None, owner = None, project = None, session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+"/tile/%s"%(tile)

        tilespec_json= self.process_simple_url_request(request_url,session)
        
        return TileSpec(json=tilespec_json)


    def get_tile_specs_from_z(self,stack,z,host = None,port = None,owner=None,project=None,
                              session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+'/z/%f/tile-specs'%(z)
        #print request_url
        tilespecs_json=self.process_simple_url_request(request_url,session)
        return [TileSpec(json=tilespec_json) for tilespec_json in tilespecs_json]

    def get_bounds_from_z(self,stack,z,host = None,port = None,owner = None,project = None,
                              session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        request_url = self.format_preamble(host,port,owner,project,stack)+'/z/%f/bounds'%(z)
        return self.process_simple_url_request(request_url,session)
       
    #
    # API for doing the bulk requests locally (i.e., to be run on the cluster)
    # Full documentation here: http://wiki.int.janelia.org/wiki/display/flyTEM/Coordinate+Mapping+Tools
    #

    MAP_COORD_SCRIPT = "/groups/flyTEM/flyTEM/render/bin/map-coord.sh"

    def set_stack_state(self,stack,state='LOADING',host = None,port = None,owner = None,project = None,
                              session=requests.session()):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        assert state in ['LOADING','COMPLETE','OFFLINE']
        request_url = self.format_preamble(host,port,owner,project,stack)+"/state/%s"%state
        print request_url
        r=session.put(request_url,data=None,headers={"content-type":"application/json"})
        return r                 
        
    def batch_local_work(self,stack, z, data, host = None, port = None, owner = None, project = None, localToWorld=False, deleteTemp=True, threads=16):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        fromJson = tempfile.NamedTemporaryFile(suffix=".json", mode='w', delete=False)
        fromJson.write(data)
        fromJson.flush()
        fromJson.close()

        toJson = tempfile.NamedTemporaryFile(suffix=".json", mode='r', delete=False)
        toJson.close()

        #cmd = "%s --owner %s --project %s --stack %s --z %d --fromJson %s --toJson %s --baseDataUrl http://tem-services.int.janelia.org:8080/render-ws/v1 --numberOfThreads %d" % (MAP_COORD_SCRIPT, owner, project, stack, z, fromJson.name, toJson.name, threads)
        cmd = "%s --owner %s --project %s --stack %s --z %d --fromJson %s --toJson %s --baseDataUrl http://10.40.3.162:8080/render-ws/v1 --numberOfThreads %d" % (MAP_COORD_SCRIPT, owner, project, stack, z, fromJson.name, toJson.name, threads)
        if localToWorld:
            cmd = cmd + " --localToWorld"
        #print(cmd)

        try:
            rc = subprocess.call(cmd, shell="True")
            if rc != 0:
                raise Exception("Invalid return code (%d): %s" % (rc, cmd))

            with open(toJson.name) as f:
                outdata = json.load(f)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return json.loads("{}")

        if deleteTemp:
            os.unlink(fromJson.name)
            os.unlink(toJson.name)

        return outdata

    def world_to_local_coordinates_batch_local(self,stack, z, data, host = None, port = None, owner = None, project = None):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        return batch_local_work(stack, z, data, host, port, owner, project, localToWorld=False)

    def local_to_world_coordinates_batch_local(self,stack, z, data, host = None, port = None, owner = None, project = None):
        (host,port,owner,project,client_scripts)=self.process_defaults(host,port,owner,project)
        return batch_local_work(stack, z, data, host, port, owner, project, localToWorld=True)
