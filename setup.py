import os
import shutil

if not os.path.isdir("logs/"):
    os.makedirs("logs/")
os.system("git clone https://github.com/ben-sb/obfuscator-io-deobfuscator")
shutil.copyfile("ts/bruh.ts", "obfuscator-io-deobfuscator/src/bruh.ts")

os.system("cd obfuscator-io-deobfuscator && bun add -D bun-types && bun install")
print("Done setting up !")