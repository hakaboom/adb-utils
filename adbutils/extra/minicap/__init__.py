# -*- coding: utf-8 -*-
import time
import threading

from loguru import logger
from adbutils.constant import (ANDROID_TMP_PATH, MNC_REMOTE_PATH, MNC_SO_REMOTE_PATH, MNC_CMD, MNC_CAP_LOCAL_PATH,
                               MNC_LOCAL_NAME, MNC_LOCAL_PATH, MNC_SO_LOCAL_PATH)
from adbutils.extra.minicap.exceptions import MinicapStartError, MinicapServerConnectError
from adbutils import ADBDevice
from adbutils._utils import NonBlockingStreamReader, reg_cleanup, SafeSocket
from adbutils._wraps import threadsafe_generator

from typing import Tuple
import struct
import subprocess


class Minicap(object):
    RECVTIMEOUT = None

    def __init__(self, device: ADBDevice, rotation_watcher=None):
        """
        初始化minicap

        Args:
            device: 设备类
            rotation_watcher: 方向监控函数
        """
        self.device = device
        self.MNC_LOCAL_NAME = MNC_LOCAL_NAME.format(device_id=self.device.device_id)  # minicap在设备上的转发名
        self.MNC_PORT = None  # minicap在电脑上使用的端口
        self.quirk_flag = 0
        self.server_flag = False  # 判断minicap服务是否启动
        self.proc = None
        self.nbsp = None

        self._update_rotation_event = threading.Event()
        if rotation_watcher:
            rotation_watcher.reg_callback(lambda x: self.update_rotation(x * 90))
        self._install_minicap()

    def __str__(self):
        return f"<minicap ({self.server_flag and 'Start' or 'Close'})> port:{self.MNC_PORT}" \
               f"\tlocal_name:{self.MNC_LOCAL_NAME}"

    def start_server(self) -> None:
        """
        开启minicap服务

        Raises:
            MinicapStartError: minicap server start error
        Returns:
            None
        """
        self._set_minicap_forward()
        param = self._get_params()
        proc = self.device.start_shell([MNC_CMD, f"-n '{self.MNC_LOCAL_NAME}'", '-P',
                                        "%dx%d@%dx%d/%d 2>&1" % param])

        nbsp = NonBlockingStreamReader(proc.stdout)
        while True:
            line = nbsp.readline(timeout=5)
            if line is None:
                raise MinicapStartError("minicap server setup timeout")
            if b'have different types' in line:
                raise MinicapStartError("minicap server setup error")
            if b"Server start" in line:
                logger.info('minicap server setup')
                break

        if proc.poll() is not None:
            raise MinicapStartError('minicap server quit immediately')
        reg_cleanup(proc.kill)
        time.sleep(.5)
        # self.proc = proc
        # self.nbsp = nbsp
        self.server_flag = True

    def teardown(self) -> None:
        """
        关闭minicap服务

        Returns:
            None
        """
        logger.debug('minicap server teardown')
        if self.proc:
            self.proc.kill()

        if self.nbsp:
            self.nbsp.kill()

        if self.MNC_PORT and self.device.get_forward_port(remote=self.MNC_LOCAL_NAME):
            self.device.remove_forward(local=f'tcp:{self.MNC_PORT}')

        self.server_flag = False

    def _set_minicap_forward(self):
        """
        设置minicap开放的端口

        Returns:
            None
        """
        # teardown服务后,保留端口信息,用于下次启动
        remote = f'localabstract:{self.MNC_LOCAL_NAME}'
        if port := self.device.get_forward_port(remote=remote, device_id=self.device.device_id):
            self.MNC_PORT = port
            return

        self.MNC_PORT = self.MNC_PORT or self.device.get_available_forward_local()
        self.device.forward(local=f'tcp:{self.MNC_PORT}', remote=remote)

    def _install_minicap(self) -> None:
        """
        check if minicap and minicap.so installed

        Returns:
            None
        """
        if not self.device.check_file(ANDROID_TMP_PATH, 'minicap'):
            self.device.push(local=MNC_LOCAL_PATH.format(abi_version=self.device.abi_version),
                             remote=MNC_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', MNC_REMOTE_PATH])

        if not self.device.check_file(ANDROID_TMP_PATH, 'minicap.so'):
            self.device.push(local=MNC_SO_LOCAL_PATH.format(abi_version=self.device.abi_version,
                                                            sdk_version=self.device.sdk_version),
                             remote=MNC_SO_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', MNC_SO_REMOTE_PATH])

    def _get_params(self) -> Tuple[int, int, int, int, int]:
        """
        获取minicap命令需要的屏幕分辨率参数

        Returns:
            None
        """
        display_info = self.device.displayInfo
        real_width = display_info['width']
        real_height = display_info['height']
        real_rotation = display_info['rotation']

        if self.quirk_flag & 2 and real_rotation in (90, 270):
            params = real_height, real_width, real_height, real_width, 0
        else:
            params = real_width, real_height, real_width, real_height, real_rotation

        return params

    def update_rotation(self, rotation):
        """
        更新屏幕方向

        Args:
            rotation: 方向角度

        Returns:
            None
        """
        logger.debug("minicap update_rotation: {}", rotation)
        self._update_rotation_event.set()

    def get_frame(self):
        """
        获取屏幕截图

        Returns:
            图像数据
        """
        if self._update_rotation_event.is_set():
            logger.info('minicap update_rotation')
            self.teardown()
            self.start_server()
            self._update_rotation_event.clear()

        try:
            return self._get_frame()
        except (ConnectionRefusedError, OSError) as err:
            self.teardown()
            raise MinicapServerConnectError(f'{err}')

    def _get_frame(self):
        s = SafeSocket()
        s.connect((self.device.host, self.MNC_PORT))
        t = s.recv(24)
        # minicap header
        global_headers = struct.unpack("<2B5I2B", t)
        # Global header binary format https://github.com/openstf/minicap#global-header-binary-format
        ori, self.quirk_flag = global_headers[-2:]

        if self.quirk_flag & 2 and ori not in (0, 1, 2):
            stopping = True
            logger.error("quirk_flag found:{}, going to resetup", self.quirk_flag)
        else:
            stopping = False

        if not stopping:
            s.send(b"1")
            if self.RECVTIMEOUT is not None:
                header = s.recv_with_timeout(4, self.RECVTIMEOUT)
            else:
                header = s.recv(4)
            if header is None:
                logger.error("minicap header is None")
            else:
                frame_size = struct.unpack("<I", header)[0]
                frame_data = s.recv(frame_size)
                s.close()
                return frame_data

        logger.info('minicap get_frame ends')
        s.close()
        self.teardown()


if __name__ == '__main__':
    import cv2
    from baseImage import Image

    from adbutils import ADBDevice
    from adbutils.extra.minicap import Minicap

    device = ADBDevice(device_id='emulator-5554')
    minicap = Minicap(device)
    minicap.start_server()

    while True:
        if img := minicap.get_frame():
            cv2.imshow('test', Image(img).imread())

        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            minicap.teardown()
