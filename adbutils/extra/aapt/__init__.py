# -*- coding: utf-8 -*-
from adbutils.constant import AAPT_LOCAL_PATH, AAPT_REMOTE_PATH, ANDROID_TMP_PATH

from typing import Union, Tuple, List, Optional, Match, Dict
import re
import time


class Aapt(object):
    def __init__(self, device):
        self.device = device
        self._install_aapt()

    def get_app_info(self, packageName: str) -> Dict[str, str]:
        """
        获取app信息

        Args:
            packageName: app包名

        Returns:
            app信息, 包含package_name、versionCode、versionName、sdkVersion、targetSdkVersion、app_name、launchable_activity
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            try:
                app_name = m.group('app_name_zh')
            except IndexError:
                app_name = m.group('app_name')

            return {
                'package_name': m.group('package_name'),
                'versionCode': m.group('versionCode'),
                'versionName': m.group('versionName'),
                'sdkVersion': m.group('sdkVersion'),
                'targetSdkVersion': m.group('targetSdkVersion'),
                'app_name': app_name,
                'launchable_activity': m.group('launchable_activity'),
            }

    def get_app_versionName(self, packageName: str) -> Optional[str]:
        """
        获取app应用程序的版本号

        Args:
            packageName: app包名

        Returns:
            app versionName
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            return m.group('versionName')

    def get_app_versionCode(self, packageName: str) -> Optional[str]:
        """
        获取app应用程序的内部版本号

        Args:
            packageName: app包名

        Returns:
            app versionCode
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            return m.group('versionCode')

    def get_app_name(self, packageName: str) -> Optional[str]:
        """
        获取app应用名称

        Args:
            packageName: app包名

        Returns:
            app name,优先返回label-zh
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            try:
                return m.group('app_name_zh')
            except IndexError:
                return m.group('app_name')

    def get_app_sdkVersion(self, packageName: str) -> Optional[str]:
        """
        获取app sdk版本

        Args:
            packageName: app包名

        Returns:
            app sdkVersion
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            return m.group('sdkVersion')

    def get_app_targetSdkVersion(self, packageName: str) -> Optional[str]:
        """
        获取app targetSdk版本

        Args:
            packageName: app包名

        Returns:
            app targetSdkVersion
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            return m.group('targetSdkVersion')

    def get_app_launchableActivity(self, packageName: str):
        """
        获取app应用名称launchable_activity

        Args:
            packageName: app包名

        Returns:
            launchable_activity
        """
        app_info = self._get_app_info(packageName)
        if m := self._parse_app_info(app_info):
            return m.group('launchable_activity')

    @staticmethod
    def _parse_app_info(app_info) -> Optional[Match[str]]:
        """
        解析aapt d badging获取到的应用信息

        Args:
            app_info: aapt获取到的应用信息

        Returns:

        """
        pattern = re.compile(r'package: name=\'(?P<package_name>\S*)\' '
                             r'versionCode=\'(?P<versionCode>\S*)\' '
                             r'versionName=\'(?P<versionName>\S*)\''
                             r'.*sdkVersion:\'(?P<sdkVersion>\d+)\''
                             r'.*targetSdkVersion:\'(?P<targetSdkVersion>\d+)\''
                             r'.*application-label-zh:\'(?P<app_name_zh>\S+)\''
                             r'.*application: label=\'(?P<app_name>\S*)\''
                             r'.*launchable-activity: name=\'(?P<launchable_activity>\S*)\'', re.DOTALL)
        m = pattern.search(app_info)
        return m if m else None

    def _get_app_info(self, packageName: str) -> Optional[str]:
        app_path = self.device.get_app_install_path(packageName)
        # badging: Print the label and icon for the app declared in APK.
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
            if 'arm' in self.device.abi_version:
                self.device.push(local=AAPT_LOCAL_PATH['arm'], remote=AAPT_REMOTE_PATH)
            else:
                self.device.push(local=AAPT_LOCAL_PATH['x86'], remote=AAPT_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', AAPT_REMOTE_PATH])
