import os

print("hello", os.environ['TYPE'], os.getpid())

if os.environ['TYPE'] == "master":
    import plyvel
    db = plyvel.DB('/tmp/testdb/', create_if_missing=True)

def master(env, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"Hello world"]

def volume(env, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"Nope world"]