"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice, ADBClient
from adbutils.extra.performance.fps import Fps


device = ADBDevice('emulator-5554')
fps = Fps(device)
# layers = fps.get_possible_layer(device.foreground_package)
print(fps.get_layers_from_buffering())

