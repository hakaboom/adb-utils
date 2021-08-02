"""
python setup.py sdist
twine upload dist/*
"""
from adbutils import ADBExtraDevice
from baseImage import IMAGE
import cv2

device = ADBExtraDevice(device_id='emulator-5554')

while True:
    img = IMAGE(device.minicap.get_frame())
    img.imshow(title='capture')
    if cv2.waitKey(25) & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        exit(0)