# -*- coding: utf-8 -*-
from adbutils.constant import AAPT_LOCAL_PATH, AAPT_REMOTE_PATH, ANDROID_TMP_PATH

from typing import Union, Tuple, List
import re
import time


class Aapt(object):
    def __init__(self, device):
        self.device = device
        self._install_aapt()

    def get_app_name(self, packageName: str):
        """
        获取app应用名称

        Args:
            packageName: app包名

        Returns:
            app name
        """
        app_info = self._get_app_info(packageName)
        if app_info:
            pattern = re.compile("application-label:\'(?P<label>.*)\'\\s?")
            m = pattern.search(app_info)
            if m:
                return m.group('label')

    def _get_app_info(self, packageName: str):
        app_path = self.device.get_app_install_path(packageName)
        ret = self.device.shell(f'{AAPT_REMOTE_PATH} d badging {app_path}')
        return ret

    def _get_app_path_list(self, flag_options: Union[None, str, list] = None) -> List[Tuple[str, str]]:
        """
        获取app的对应地址

        Args:
            flag_options: 获取app_list可指定参数

        Returns:
            app_path_list: tuple[app_path, packageName]
        """
        options = ['-f']
        if isinstance(flag_options, list):
            if '-f' not in flag_options:
                options += flag_options
        elif isinstance(flag_options, str):
            options += [flag_options]
        app_list = self.device.app_list(options)
        pattern = re.compile('^(\\S+)=(\\S+)$')
        ret = []
        for app in app_list:
            m = pattern.findall(app)
            if m:
                ret.append(m[0])

        return ret

    def _install_aapt(self) -> None:
        """
        check if aapt installed

        Returns:
            None
        """
        if not self.device.check_file(ANDROID_TMP_PATH, 'aapt'):
            self.device.push(local=AAPT_LOCAL_PATH.get(self.device.abi_version), remote=AAPT_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', AAPT_REMOTE_PATH])
