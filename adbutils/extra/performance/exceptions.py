# -*- coding: utf-8 -*-
from adbutils.exceptions import AdbBaseError


class AdbProcessNotFound(AdbBaseError):
    """ An error while dumpsys meminfo process not found """


class AdbNoInfoReturn(AdbBaseError):
    """ An error while adb shell did not return the correct result """
