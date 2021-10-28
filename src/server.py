import os
import time
import xattr
import json
import random
import socket
import hashlib
import tempfile

print("hello", os.environ['TYPE'], os.getpid())

def resp(sr, code, headers=[("Content-Type", "text/plain")], body=b''):
    sr(code, headers)
    return [body]

# *** Master server ***

if os.environ['TYPE'] == "master":
    # check on volume servers
    # comma separated values (csv)
    volumes = os.environ['VOLUMES'].split(",")

    for v in volumes:
        print(v)

    import plyvel
    db = plyvel.DB(os.environ['DB'], create_if_missing=True)


def master(env, sr):
    key = env['REQUEST_URI']

    if env['REQUEST_METHOD'] == 'POST':
        # POST is called by the volume servers to write to the database
        flen = int(env.get('CONTENT_LENGTH', '0'))
        if flen > 0:
            db.put(key.encode('utf-8'), env['wsgi.input'].read(), sync=True)
        else:
            db.delete(key.encode('utf-8')) 
        return resp(sr, '200 OK')

    metakey = db.get(key.encode('utf-8'))
    print(env)

    if metakey is None:
        if env['REQUEST_METHOD'] == 'PUT':
            # handle putting key
            # TODO: MAKE volume selection intelligent -> load balancing
            volume = random.choice(volumes)
        else:    
            # this key doesn't exist and we aren't trying to create it
            return resp(sr, '404 Not Found')
    else:
        # key found
        if env['REQUEST_METHOD'] == 'PUT':
            # we are trying to put it. DELETE first!
            return resp(sr, '409 Conflict')
        meta = json.loads(metakey.decode('utf-8'))
        volume = meta['volume']

    # send the redirect
    headers = [('Location', 'http://%s%s' % (volume, key))]

    return resp(sr, '307 Temporary Redirect', headers)

# *** Volume server ***

class FileCache(object):
    # This is a single computer on disk key value store

    def __init__(self, basedir):
        self.basedir = os.path.realpath(basedir)
        self.tmpdir = os.path.join(self.basedir, "tmp")
        os.makedirs(self.tmpdir, exist_ok=True)
        print("FileCache in %s" % basedir)


    def k2p(self, key, mkdir_ok=False):
        # must be MD5 hash
        key = hashlib.md5(key).hexdigest()

        # 2 layers deep in nginx world
        path = self.basedir+"/"+key[0:2]+"/"+key[0:4]
        if not os.path.isdir(path) and mkdir_ok:
            # exist ok is fine, could be a race
            os.makedirs(path, exist_ok=True)

        return os.path.join(path, key)

    def exists(self, key):
        return os.path.isfile(self.k2p(key))

    def delete(self, key):
        os.unlink(self.k2p(key))

    def get(self, key):
        return open(self.k2p(key), "rb")

    def put(self, key, stream):
        with tempfile.NamedTemporaryFile(dir = self.tmpdir, delete=False) as f:
            # TODO: in chucks, don't waste RAM
            f.write(stream.read())

            # save the real name in xattr in case we rebuild it
            xattr.setxattr(f.name , 'user.key', key)
            # TODO: check hash
            os.rename(f.name, self.k2p(key, True))

if os.environ['TYPE'] == "volume":
    host = os.environ['HOST'] + ":" + os.environ['PORT']
    print(host)

    # create the filecache 
    fc = FileCache(os.environ['VOLUME'])

def volume(env, sr):
    key = env['REQUEST_URI'].encode('utf-8')

    if env['REQUEST_METHOD'] in ['PUT']:
        if fc.exists(key):
            # can't write already exists
            return resp(sr, '409 Conflict')
        flen = int(env.get('CONTENT_LENGTH', '0'))
        if flen > 0:
            fc.put(key, env['wsgi.input'])
            # notify database

            return resp(sr, '201 Created')
        else:
            return resp(sr, '411 Length Required')

    if not fc.exists(key):
        # key not in the FileCache, 404
        return resp(sr, '404 Not Found')
            
    if env['REQUEST_METHOD'] in ['GET']:
        # TODO: in chunks, don't waste RAM
        return resp(sr, '200 OK', body=fc.get(key).read())

    if env['REQUEST_METHOD'] in ['DELETE']:
        fc.delete(key)
        return resp(sr, '204 OK')



