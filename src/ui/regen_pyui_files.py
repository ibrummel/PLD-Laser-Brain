import os
import subprocess

root = os.getcwd()
ui_files = [os.path.join(root, f) for f in os.listdir(root) if f.endswith('.ui')]

for file in ui_files:
    # Use this on windows
    #subprocess.run(["pyuic5", '"' + file + '"', "-o", '"' + file.replace(".ui", ".py") + '"'])
    # Use this on linux
    subprocess.run(["pyuic5", file, "-o", file.replace(".ui", ".py")])