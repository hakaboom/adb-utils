"""
python setup.py sdist
twine upload dist/*
"""
import re

from adbutils import ADBExtraDevice

device = ADBExtraDevice(device_id='emulator-5554', aapt=True)
# print(device.shell(['busybox']))
meminfo = device.shell(['dumpsys', 'meminfo'])
# print(meminfo)
pattern = re.compile(r'Total PSS by process:\r\n   (.*)\r\n   ', re.DOTALL)
print(pattern.findall(meminfo))
# pattern = re.compile(r'\s(\d+) kB: (\S+)\s*\(pid (\d+).*\)')
# if m := pattern.findall(meminfo):
#     for i in m:
#         print(i)