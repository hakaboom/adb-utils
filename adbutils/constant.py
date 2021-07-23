# -*- coding: utf-8 -*-
import os


STATICPATH = os.path.join(os.path.abspath('adbutils'), 'static')
DEFAULT_ADB_PATH = {
    "Windows": os.path.join(STATICPATH, "adb", "windows"),
    "Darwin": os.path.join(STATICPATH, "adb", "mac", "adb"),
    "Linux": os.path.join(STATICPATH, "adb", "linux", "adb"),
    "Linux-x86_64": os.path.join(STATICPATH, "adb", "linux", "adb"),
    "Linux-armv7l": os.path.join(STATICPATH, "adb", "linux_arm", "adb"),
}
ANDROID_ADB_SERVER_HOST = '127.0.0.1'
ANDROID_ADB_SERVER_PORT = 5037


ADB_CAP_LOCAL_PATH = '/data/local/tmp/screencap.raw'
