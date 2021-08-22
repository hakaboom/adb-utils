"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice, ADBClient

device = ADBDevice('192.168.50.164:5555')
print(device.running_activities)


