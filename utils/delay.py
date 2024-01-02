import time
from flask import request
import gevent
from constants import BAD_REQUEST, flask_app

BAD_REQUEST = ("BAD REQUEST !", 400)

@flask_app.route("/delay")
def get_delay():
    delay = request.args.get("time")
    if not delay:
        return ("No time argument provided.", 400)
    try:
        delay = int(delay)
    except:
        return ("Provided delay argument not an int.", 400)

    if delay < 1 or delay > 20:
        return ("Delay must be in a range of 1-20", 400)

    gevent.sleep(delay)

    return f"Done waiting for {delay} seconds"
