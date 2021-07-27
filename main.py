"""
python setup.py sdist
twine upload dist/*
"""
from adbutils import ADBDevice

android = ADBDevice(device_id='emulator-5554')
print(android.android_version)