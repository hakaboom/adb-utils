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

