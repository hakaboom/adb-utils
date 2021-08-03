"""
python setup.py sdist
twine upload dist/*
"""
from adbutils import ADBExtraDevice

device = ADBExtraDevice(device_id='emulator-5554')
device.minicap.start_server()
device.minicap.get_frame()
device.minicap.teardown()