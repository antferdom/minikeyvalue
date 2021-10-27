### API

- GET /key
  - Supports range requests.
  - 302 redirect to volume server.
- {PUT, DELETE} /key
  - Blocks. 200 = written, anythin else = nothing happened.

### Start Master Server (default port 3000)

```bash
$ ./master /tmp/cachedb/
```

### Sart Volume Server (default port 3001)

```bash
# Should create a temporal directoy at /tmp/volume1
$ ./volume
.. ..
hello volume 14845
FileCache in /tmp/volume1/

$ ./volume /tmp/volume1/ localhost:3000
PORT=3002 ./volume -p 3002 /tmp/volume2/ localhost:3000
```

### Usage

```bash
# PUT "bigswag" in key "wehave"
$ curl -X PUT -d bigswag localhost:3000/wehave

# GET key "wehave" (should be "bigswag")
$ curl -X GET localhost:3000/wehave

# Delete key "wehave"
$ curl -X DELETE localhost:3000/wehave
```

# Architecture

## How volumes servers are discovered



