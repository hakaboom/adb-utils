# -*- coding: utf-8 -*-
from adbutils.constant import ADB_INSTALL_FAILED


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


# ---------------------------------BaseError---------------------------------
class AdbSDKVersionError(BaseError):
    """Errors caused by insufficient sdb versions """


class AdbTimeout(BaseError):
    """ Adb command time out"""


class NoDeviceSpecifyError(BaseError):
    """ No device was specified when ADB was commanded """


class AdbDeviceConnectError(BaseError):
    """ failed to connect device """


class AdbInstallError(BaseError):
    """ An error while adb install apk failed """
    def __repr__(self):
        if self.message in ADB_INSTALL_FAILED:
            return repr(ADB_INSTALL_FAILED[self.message])
        else:
            return repr(f'adb install failed,\n{self.message}')

    def __str__(self):
        return repr(self)