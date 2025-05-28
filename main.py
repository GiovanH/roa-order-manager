from roa import RoaFile

import os

from pathlib import Path

ROA_DIR = Path(f"{os.environ['LOCALAPPDATA']}/RivalsofAether/workshop")



if __name__ == '__main__':
    order_roa = RoaFile(ROA_DIR / 'order.roa', b'order.roa')
