
import os 

TS_BASE = "./@types/ol/"

fw = os.walk(TS_BASE)

while True:
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if not _file.endswith(".d.ts"):
                full_path = os.path.join(curr_dir_info[0], _file)
                os.remove(full_path)
    except StopIteration:
        break
