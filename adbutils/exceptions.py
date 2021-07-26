# -*- coding: utf-8 -*-
from adbutils.constant import ADB_INSTALL_FAILED


class AdbError(Exception):
    """ There was an exception that occurred while ADB command """
    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        return f"stdout[{self.stdout}] stderr[{self.stderr}]"


class AdbShellError(AdbError):
    """ There was an exception that occurred while ADB shell command """


# ---------------------------------BaseError---------------------------------

class BaseError(Exception):
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return repr(self.message)


class AdbBaseError(BaseError):
    """ There was an exception that occurred while ADB command """


class AdbSDKVersionError(AdbBaseError):
    """Errors caused by insufficient sdb versions """


class AdbTimeout(AdbBaseError):
    """ Adb command time out"""


class NoDeviceSpecifyError(AdbBaseError):
    """ No device was specified when ADB was commanded """


class AdbDeviceConnectError(AdbBaseError):
    """ Failed to connect device """


class AdbInstallError(AdbBaseError):
    """ An error while adb install apk failed """
    def __repr__(self):
        if self.message in ADB_INSTALL_FAILED:
            return repr(ADB_INSTALL_FAILED[self.message])
        else:
            return repr(f'adb install failed,\n{self.message}')

    def __str__(self):
        return repr(self)