#!./.venv/bin/python
import json
from gevent.pywsgi import WSGIServer
import subprocess
from time import strftime
# Import back offsetfinder if fixed. For now using a diff service.
# import aniwave.offsetfinder
import aniwave.keys

import netu.imagefinder

import utils.delay
import utils.echoback
from constants import flask_app

# in utils/delay, we use time.sleep()
# if just used like this, it'll block the whole thread.
# However, if we use monkey.patch_time(), it'll replace time.sleep by gevent.sleep
# from gevent import monkey; 
# monkey.patch_time()
# Just ended up using gevent.sleep(), but this is pretty cool tbh

if __name__ == "__main__":
    print("Loading env")
    # load env
    env = None
    try: 
        with open("env.json") as file: env = json.load(file)
    except: pass

    print("Done loading, starting webserver")
    # set webserver
    http_server = WSGIServer(('', 11481), flask_app)

    # bun deobfuscator part for aniwave
    # bun_executable = None
    # if env:
    #     bun_executable = env.get("Z_BUN_EXECUTABLE")
    # if not bun_executable:
    #     bun_executable = "bun"
    
    # file = open(f"logs/{strftime('%Y_%m_%d_%Hh%M')}_deobf_out.txt", "w")
    # deobf_process = subprocess.Popen([bun_executable, "src/bruh.ts"], stdout=file, cwd="obfuscator-io-deobfuscator", env=env)
    
    # handle errors
    err = ""
    try:
        http_server.serve_forever()
    except KeyboardInterrupt: err = "KeyboardInterrupt"
    except Exception as e: err = e
    print(f"{err} received; stopping.")
    # deobf_process.kill()
    # file.close()
        