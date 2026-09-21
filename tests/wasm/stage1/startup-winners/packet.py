#!/usr/bin/env python3
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('startup_packet',HERE.parent/'startup-joined/packet.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p.main(HERE)
