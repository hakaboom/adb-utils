from adbutils import ADBDevice
import datetime

device = ADBDevice(device_id='emulator-5554')
while True:
    device.shell('cd')
    print(datetime.datetime.now())