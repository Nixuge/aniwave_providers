#!/bin/python3
import json
from gevent.pywsgi import WSGIServer
import subprocess
from time import strftime
import aniwave.offsetfinder
import netu.imagefinder
from constants import flask_app

if __name__ == "__main__":
    # load env
    env = None
    try: 
        with open("env.json") as file: env = json.load(file)
    except: pass

    # set webserver
    http_server = WSGIServer(('', 11481), flask_app)

    # bun deobfuscator part for aniwave
    file = open(f"logs/{strftime('%Y_%m_%d_%Hh%M')}_deobf_out.txt", "w")
    deobf_process = subprocess.Popen(["bun", "src/bruh.ts"], stdout=file, cwd="obfuscator-io-deobfuscator", env=env)
    
    # handle errors
    err = ""
    try:
        http_server.serve_forever()
    except KeyboardInterrupt: err = "KeyboardInterrupt"
    except Exception as e: err = e
    print(f"{err} received; stopping.")
    deobf_process.kill()
    file.close()
        