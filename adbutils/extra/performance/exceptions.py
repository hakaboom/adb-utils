# -*- coding: utf-8 -*-
from adbutils.exceptions import AdbBaseError


class AdbProcessNotFound(AdbBaseError):
    """ An error while dumpsys meminfo process not found """
