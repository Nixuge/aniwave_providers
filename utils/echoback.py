from dataclasses import dataclass
import random
import string
import time
from flask import request
import gevent
from constants import BAD_REQUEST, flask_app

MAX_SAVED_CONTENT_COUNT = 100
EXPIRE_DELAY_MS = 600_000 # 10min

@dataclass
class SavedContent:
    expire_time: int
    content: str
    # extension: str # saved in dict, unneeded

saved: dict[str, SavedContent] = {}

@flask_app.route("/echo/add", methods=["POST"])
def echo_add():
    # Cleanup if too many entries
    while len(saved) > MAX_SAVED_CONTENT_COUNT:
        (k := next(iter(saved)), saved.pop(k))

    current_time_ms = time.time_ns() // 1_000_000
    # Cleanup expired entries (can't remove while iterating from dict so doing it after)
    toPop = []
    for filename, entry in saved.items():
        if entry.expire_time >= current_time_ms:
            toPop.append(filename)
    for filename in toPop: 
        saved.pop(filename)

    # Parse input data
    if not request.is_json:
        return ("Request must have json data incoming", 400)
    # request.json
    content = request.json.get("content")
    if not content:
        return ("No content provided.", 400)
    if len(content) > 10000:
        return ("Content too long.", 400)
    ext = request.json.get("extension", "")
    if len(ext) > 0 and ext[0] != ".":
        ext = "." + ext
    
    saved_content = SavedContent(current_time_ms + EXPIRE_DELAY_MS, content)
    result_filename = ''.join((random.choice(string.ascii_lowercase) for _ in range(16))) + ext

    saved[result_filename] = saved_content

    return result_filename

@flask_app.route("/echo/<path>", methods=["GET"])
def echo_get(path):
    if path == "add":
        return ("Wrong method, please use a post to add an echo.", 400)
    contentObj = saved.get(path)
    if not contentObj:
        return ("Invalid filepath", 400)
    
    return contentObj.content