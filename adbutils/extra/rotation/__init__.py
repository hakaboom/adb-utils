#! usr/bin/python
# -*- coding:utf-8 -*-
import os
import time
import threading
import traceback
from loguru import logger


class Rotation(object):
    def __init__(self, device):
        self.device = device
        self._kill_event = threading.Event()
        self.current_orientation = None
        self._t = None
        self.ow_callback = []

    def start(self):

        def _refresh_by_adb():
            ori = self.device.getDisplayOrientation()
            return ori

        def _run(kill_event):
            while not kill_event.is_set():
                ori = _refresh_by_adb()
                if self.current_orientation == ori:
                    time.sleep(2)
                    continue
                if ori is None:
                    continue
                logger.info('update orientation {}->{}'.format(self.current_orientation, ori))
                self.current_orientation = ori
                for callback in self.ow_callback:
                    try:
                        callback(ori)
                    except:
                        logger.error('callback: {} error'.format(callback))
                        traceback.print_exc()

        self.current_orientation = _refresh_by_adb()
        self._t = threading.Thread(target=_run, args=(self._kill_event,), name='rotationwatcher')
        self._t.daemon = True
        self._t.start()
        return self.current_orientation

    def reg_callback(self, ow_callback):
        """
        Args:
            ow_callback:
        Returns:
        """
        """方向变化的时候的回调函数，参数一定是ori"""
        self.ow_callback.append(ow_callback)
