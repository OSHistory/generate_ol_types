
import os 
import shutil 

BASE_PATH = "./node_modules/ol/src/ol/"
TS_TARGET = "./@types/ol/"
fw = os.walk(BASE_PATH)

while True: 
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if not _file.endswith(".js"):
                continue 
            full_path = os.path.join(curr_dir_info[0], _file)
            tmp_path = os.path.join(
                TS_TARGET, 
                curr_dir_info[0].replace(BASE_PATH, ""), 
                _file.replace(".js", ".ts")
            )
            if not os.path.exists(os.path.dirname(tmp_path)):
                os.makedirs(os.path.dirname(tmp_path))
            shutil.copy(full_path, tmp_path)

    except StopIteration:
        break