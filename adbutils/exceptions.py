# -*- coding: utf-8 -*-
from adbutils.constant import ADB_INSTALL_FAILED


class AdbBaseError(Exception):
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return repr(self.message)


class AdbError(AdbBaseError):
    """ There was an exception that occurred while ADB command """
    def __init__(self, stdout, stderr, message: str = None):
        super(AdbError, self).__init__(message=message)
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        return f"stdout[{self.stdout}] stderr[{self.stderr}]"


class AdbShellError(AdbError):
    """ There was an exception that occurred while ADB shell command """


class AdbSDKVersionError(AdbBaseError):
    """Errors caused by insufficient sdb versions """


class AdbTimeout(AdbBaseError):
    """ Adb command time out"""


class NoDeviceSpecifyError(AdbBaseError):
    """ No device was specified when ADB was commanded """


class AdbDeviceConnectError(AdbBaseError):
    """ Failed to connect device """
    CONNECT_ERROR = r"error:\s*(" \
                    r"(device \'\S+\' not found)|" \
                    r"(cannot connect to daemon at [\w\:\s\.]+ Connection timed out)|" \
                    r"(device offline))"


class AdbInstallError(AdbBaseError):
    """ An error while adb install apk failed """
    def __repr__(self):
        return repr(str(self))

    def __str__(self):
        if self.message in ADB_INSTALL_FAILED:
            return ADB_INSTALL_FAILED[self.message]
        else:
            return f'adb install failed,\n{self.message}'
