import renderapi

def test_render_client():
    args={
        'host':'renderhost',
        'port':8080,
        'owner':'renderowner',
        'project':'renderproject',
        'client_scripts':'/path/to/client_scripts'
    }
    r = renderapi.render.connect(**args)
