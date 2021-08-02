"""
python setup.py sdist
twine upload dist/*
"""
from adbutils import ADBExtraDevice

device = ADBExtraDevice(device_id='emulator-5554')
print(device.aapt.get_app_name('com.njh.biubiu'))