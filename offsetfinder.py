from dataclasses import dataclass
import hashlib
import json
import re
import time
from gevent.pywsgi import WSGIServer
import subprocess
from time import strftime

import requests


false = False
true = True

MATCH_KEYS_OBFUSCATED = """loading\(\);
            var _0x[a-z0-9]{6} = _0x[a-z0-9]{6}\((.*?), this\.[a-zA-Z]\);
            _0x[a-z0-9]{6} = _0x[a-z0-9]{6}\((.*?), """

MATCH_OFFSET_FINDER = """  function %DATA1%\(_0x[a-z0-9]{6}, _0x[a-z0-9]{6}\) {
    var _0x[a-z0-9]{6} = (_0x[a-z0-9]{6})\(\);
    _0x[a-z0-9]{6} = function \(_0x[a-z0-9]{6}, _0x[a-z0-9]{6}\) {
      _0x[a-z0-9]{6} = _0x[a-z0-9]{6} - ([0-9]*);
      var _0x[a-z0-9]{6} = _0x[a-z0-9]{6}\[_0x[a-z0-9]{6}\];
      return _0x[a-z0-9]{6};
    }"""

MATCH_KEYPART_OFFSET_FIRST = """  var %DATA1% = (_0x[a-z0-9]{6})\(([0-9]*)\);"""
MATCH_KEYPART_OFFSET = """  var %DATA1% = _0x[a-z0-9]{6}\(([0-9]*)\);"""

MATCH_DATA_ARRAY = """  function %DATA1%\(\) {
    var _0x[a-z0-9]{6} = (.*?);"""

MATCH_ARRAY_SHIFTER = """while \(true\) {
      try {
        var _0x[a-z0-9]{6} = (.*?);
        if \(_0x[a-z0-9]{6} === _0x[a-z0-9]{6}\) {
          break;
        } else {
          _0x[a-z0-9]{6}\.push\(_0x[a-z0-9]{6}\.shift\(\)\);
        }
      } catch \(_0x[a-z0-9]{6}\) {
        _0x[a-z0-9]{6}\.push\(_0x[a-z0-9]{6}\.shift\(\)\);
      }
    }
  }\)\(_0x[a-z0-9]{6}, ([0-9]*?)\);"""

# thanks to https://gist.github.com/lsauer/6088767
# to reimplement _normalize_array
def parseInt(sin):
  import re
  return int(''.join([c for c in re.split(r'[,.]',str(sin))[0] if c.isdigit()])) if re.match(r'\d+', str(sin), re.M) and not callable(sin) else None

@dataclass
class KeyPart:
    data: str
    isRawString: bool
    offset: int | None = None

class KeyFinder:
    key_1: list[KeyPart]
    key_2: list[KeyPart]
    offset_find_function: str
    array_get_function: str
    data_array: list[str]
    global_offset: int
    shift_target: int
    free_rce: str
    def __init__(self, data: str) -> None:
        self.key_1 = []
        self.key_2 = []
        # js function that gets called for every obf value in the js
        self.offset_find_function = ""
        # js function that gets called to get the element in the array
        self.array_get_function = ""
        self.data_array = []
        self.global_offset = 0
        self.shift_target = 0
        self.free_rce = ""

        self.data = data

    def grab_keys(self):
        self._grab_obfuscated_key_values()
        self._grab_obfuscated_keypart_offsets()
        self._grab_global_offset()
        self._grab_data_array()
        self._grab_data_array_shifter()
        self._shift_data_array()
        self._grab_obfuscated_keypart_data()
        return (self._keyparts_to_string(self.key_1), self._keyparts_to_string(self.key_2))
    
    def _parse_key(self, key: str) -> list[KeyPart]:
        parts: list[KeyPart] = []
        for part in key.split(" + "):
            if "'" in part or '"' in part:
                parts.append(KeyPart(part.replace('"', '').replace("'", ""), true))
            else:
                parts.append(KeyPart(part, false))
        return parts

    def _grab_obfuscated_key_values(self):
        keys = re.search(MATCH_KEYS_OBFUSCATED, self.data).groups()
        self.key_1 = self._parse_key(keys[0])
        self.key_2 = self._parse_key(keys[1])

    def _grab_obfuscated_keypart_offsets(self):
        for key_parts in (self.key_1, self.key_2):
            for key_part in key_parts:
                
                if key_part.isRawString: continue
                func, offset = re.search(MATCH_KEYPART_OFFSET_FIRST.replace("%DATA1%", key_part.data), self.data).groups()
                if self.offset_find_function == "":
                    self.offset_find_function = func
                
                elif self.offset_find_function != func:
                    raise Exception("FUNCTIONS AREN'T THE SAME !")

                # else:
                    # offset = re.search(MATCH_KEYPART_OFFSET.replace("%DATA1%", key_part.data), self.data).groups()[0]
                key_part.offset = int(offset)


    def _grab_global_offset(self):
        if self.offset_find_function == "":
            raise Exception("self.offset_find_function is empty.")
        findings = re.search(MATCH_OFFSET_FINDER.replace("%DATA1%", self.offset_find_function), self.data).groups()
        self.array_get_function = findings[0]
        self.global_offset = int(findings[1])


    def _grab_data_array(self):
        if self.array_get_function == "":
            raise Exception("self.array_get_function is empty.")
        
        arr = re.search(MATCH_DATA_ARRAY.replace("%DATA1%", self.array_get_function), self.data).groups()[0]
        self.data_array = json.loads(arr.replace("'", '"'))
    
    def _grab_data_array_shifter(self):
        shift_funcs = re.findall(MATCH_ARRAY_SHIFTER, self.data)
        if len(shift_funcs) != 2:
            raise Exception("Couldn't find 2 data_array shift functions")
        good = shift_funcs[-1]
        func_to_parse = good[0]
        self.shift_target = int(good[1])
        res = re.sub("parseInt\(_0x[a-z0-9]{6}\(([0-9]*?)\)\)", "parseInt(result_arr[\g<1>-self.global_offset])", func_to_parse)
        self.free_rce = res

    def _shift_data_array(self):
        result_arr = self.data_array
        while True:
            try:
                # Calculate a value using multiple calls to the same array (result_array)
                calculated_value = eval(self.free_rce)


                # Check if the calculated value is equal to the target value
                if calculated_value == self.shift_target:
                    break
                else:
                    result_arr.append(result_arr.pop(0))
            except Exception as error:
                # print(error)
                # Handle any errors by shifting elements in the array
                result_arr.append(result_arr.pop(0))


    def _grab_obfuscated_keypart_data(self):
        if self.global_offset == 0:
            raise Exception("self.global_offset is 0, which I don't think can happen.")
        print(f"Global offset: {self.global_offset}")
        for key_parts in (self.key_1, self.key_2):
            for key_part in key_parts:
                if key_part.isRawString: continue
                corrected_offset = key_part.offset - self.global_offset
                key_part.data = self.data_array[corrected_offset]
                key_part.isRawString = true
                key_part.offset = None

    @classmethod
    def _keyparts_to_string(cls, key_parts: list[KeyPart]):
        final_str = ""
        for key_part in key_parts:
            if not key_part.isRawString:
                raise Exception(f"key_part isn't a rawString: {key_part}")
            final_str += key_part.data
        return final_str


# ========= IMPLEMENTED ALGORITHM PARTS =========
# function that gets called 2x
def rc4_encrypt_decrypt(key, data):
    # Initialization
    state = list(range(256))

    # Key Scheduling Algorithm (KSA)
    key_length = len(key)
    j = 0
    for i in range(256):
        j = (j + state[i] + ord(key[i % key_length])) % 256

        # Swap values
        state[i], state[j] = state[j], state[i]

    # Pseudo-Random Generation Algorithm (PRGA) and Output
    result = ''
    i = 0
    j = 0
    for k in range(len(data)):
        i = (i + 1) % 256
        j = (j + state[i]) % 256

        # Swap values
        state[i], state[j] = state[j], state[i]

        # XOR operation and append to result
        result += chr(ord(data[k]) ^ state[(state[i] + state[j]) % 256])

    return result

# function that gets called 1x after the rc4_encrypt_decrypt
# the default base64encode doesn't seem to do its job properly, so using this here.
def custom_base64_encode(input_string):
    epic_string = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    input_string = str(input_string)

    # Check if input contains valid characters
    for char in input_string:
        if ord(char) > 255:
            return None  # Invalid character in input

    result = ''
    i = 0
    while i < len(input_string):
        arr = [None, None, None, None]
        arr[0] = ord(input_string[i]) >> 2
        arr[1] = (3 & ord(input_string[i])) << 4

        if i + 1 < len(input_string):
            arr[1] |= ord(input_string[i + 1]) >> 4
            arr[2] = (15 & ord(input_string[i + 1])) << 2

        if i + 2 < len(input_string):
            arr[2] |= ord(input_string[i + 2]) >> 6
            arr[3] = 63 & ord(input_string[i + 2])

        for val in arr:
            result += '=' if val is None else epic_string[val]

        i += 3

    return result

# futoken
def futoken(v, location):
    # apparently "k" changes sometimes, but it doesn't really matter?
    # if possible, should still grab it.
    k = 'ViFRsqNPsIHKpYB0WLBjGjDGLa4flllPaeQmJ2GWwnXjR6wupwiKOdg92mKTSXrGkg=='
    a = [k]
    
    for i in range(len(v)):
        a.append(ord(k[i % len(k)]) + ord(v[i]))


    return 'https://mcloud.bz/mediainfo/' + ','.join(map(str, a)) + location  # Assuming location is defined somewhere
    # response = requests.get('mediainfo/' + ','.join(map(str, a)) + location)
    
    # return response.json()

def get_url(keys: tuple[str, str], full_url: str):
    video_id = re.search("e\/([a-zA-Z0-9]*)\?", full_url).groups()[0]
    # video_id = "11v69m"
    # print(video_id)
    first_pass = rc4_encrypt_decrypt(keys[0], video_id)
    second_pass = rc4_encrypt_decrypt(keys[1], first_pass)
    # print(second_pass)
    second_pass_encoded = custom_base64_encode(second_pass)
    # print(second_pass_encoded)
    url_end = "?" + full_url.split("?")[-1]
    # return futoken(second_pass_encoded, "?t=4xjQC%2F0mBlMLxA%3D%3D&autostart=true")
    return futoken(second_pass_encoded, url_end)

# ========= WEBSERVER PART =========


from flask import Flask, request
app = Flask(__name__)

JS_CACHE: dict[str, tuple[str, str]] = {}
BAD_REQUEST = ("BAD REQUEST !", 400)

@app.route("/get_video_url")
def get_video_url():
    data = request.json
    try:
        initial_url = data["url"]
        embed_js = data["embed.js"]
        embed_js = embed_js.encode('utf-8')
        if len(embed_js) < 100000 or len(embed_js) > 3000000:
            return BAD_REQUEST
        
        embed_js_hash = hashlib.md5(embed_js).hexdigest()
        keys = JS_CACHE.get(embed_js_hash)
        while keys == "PENDING":
            time.sleep(1)
        if not keys:
            JS_CACHE[embed_js_hash] = "PENDING"
            deobf = requests.post("http://localhost:48777", data=embed_js).text
            if deobf == "Invalid input.": 
                return BAD_REQUEST
            keys = KeyFinder(deobf).grab_keys()
            JS_CACHE[embed_js_hash] = keys
        return get_url(keys, initial_url)
    except:
        return BAD_REQUEST

if __name__ == "__main__":
    http_server = WSGIServer(('', 11481), app)
    file = open(f"logs/{strftime('%Y_%m_%d_%Hh%M')}_deobf_out.txt", "w")
    deobf_process = subprocess.Popen(["bun", "src/bruh.ts"], stdout=file, cwd="obfuscator-io-deobfuscator")
    err = ""
    try:
        http_server.serve_forever()
    except KeyboardInterrupt: err = "KeyboardInterrupt"
    except Exception as e: err = e
    print(f"{err} received; stopping.")
    deobf_process.kill()
    file.close()
        