# -*- coding: utf-8 -*-

class BaseError(Exception):
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return repr(self.message)


class AdbError(Exception):
    """ There was an exception that occurred while ADB command """
    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        return f"stdout[{self.stdout}] stderr[{self.stderr}]"


class AdbShellError(AdbError):
    """ There was an exception that occurred while ADB shell command """


class AdbTimeout(BaseError):
    """ Adb command time out"""


class NoDeviceSpecifyError(BaseError):
    """ No device was specified when ADB was commanded """


class AdbDeviceConnectError(BaseError):
    """ failed to connect device """
