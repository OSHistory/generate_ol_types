
import subprocess 
import os
import shutil 

TS_BASE = "./@types/ol/"

fw = os.walk(TS_BASE)

while True: 
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if _file.endswith(".d.ts"):
                continue
            if _file.endswith(".ts"):
                ts_path = os.path.join(curr_dir_info[0], _file)
                declaration_path = ts_path.replace(".ts", ".d.ts")
                if not os.path.exists(declaration_path):
                    subprocess.call(["npx", "tsc", "-d", ts_path])
    except StopIteration:
        break