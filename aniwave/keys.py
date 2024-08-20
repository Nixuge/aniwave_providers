import time
import httpx
from constants import flask_app

# Can't have dangling vars in global.
class Vals:
    keys_cache = []
    last_check = 0

@flask_app.route("/thanksForTheServerRessources", methods=["GET"])
def get_keys():
    return Vals.keys_cache

@flask_app.route("/thanksForTheServerRessources", methods=["POST"])
def refresh_keys():
    # TODO: CHECK USING USER PROVIDED URL. FOR NOW JUST DOING IT THE YOLO WAY.

    if (time.time() - Vals.last_check) < 1800:
        return Vals.keys_cache, 418 # i'm a teapot
    
    print("Refreshing Aniwave keys")
    attempts = 0
    res = None
    while res == None and attempts < 3:
        try:
            print("Attempting to grab keys.")
            res = httpx.request("POST", "https://anithunder.vercel.app/api/keys", timeout=20).json()
        except Exception as e:
            print("Exception happened while grabbing keys:")
            print(e)
        attempts += 1
    
    if attempts == 4:
        return ["Fuck you"], 500

    Vals.keys_cache = res
    Vals.last_check = time.time()
    print("Done refreshing Aniwave keys")
    return res

refresh_keys()
