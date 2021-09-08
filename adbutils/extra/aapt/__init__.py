# -*- coding: utf-8 -*-
from adbutils import ADBDevice
from adbutils.constant import AAPT_LOCAL_PATH, AAPT_REMOTE_PATH, ANDROID_TMP_PATH
from adbutils.exceptions import AdbBaseError

from typing import Union, Tuple, List, Optional, Match, Dict
import re
import time


class Aapt(object):
    def __init__(self, device: ADBDevice):
        self.device = device
        self._install_aapt()

    def get_app_info(self, name: str) -> Dict[str, Optional[str]]:
        """
        获取app信息

        Args:
            name: app包名

        Returns:
            app信息, 包含:package_name/versionCode/versionName/sdkVersion/targetSdkVersion/app_name/launchable_activity
        """
        app_info = self._get_app_info(name)

        ret = {'sdkVersion': None, 'targetSdkVersion': None, 'launchable_activity': None}

        # step1: 获取几个基础参数
        if baseInfo := re.compile(r'package: name=\'(?P<package_name>\S*)\' '
                                  r'versionCode=\'(?P<versionCode>\S*)\' '
                                  r'versionName=\'(?P<versionName>[\s\S]*)\' '
                                  r'platformBuildVersionName=\'(?P<platformBuildVersionName>\S*)\'').search(app_info):
            for key, value in baseInfo.groupdict().items():
                ret[key] = value

        # step2: 获取sdk版本
        if sdkVersionInfo := re.compile(r'sdkVersion:\'(?P<sdkVersion>\d+)\'').search(app_info):
            ret['sdkVersion'] = sdkVersionInfo.group('sdkVersion')

        # step3: 获取目标sdk版本
        if targetSdkVersionInfo := re.compile(r'targetSdkVersion:\'(?P<targetSdkVersion>\d+)\'').search(app_info):
            ret['targetSdkVersion'] = targetSdkVersionInfo.group('targetSdkVersion')

        # step4: 获取app名字
        localesLabel = re.compile(r"application-label-(\S*):\'([ \S]+)\'").findall(app_info)
        for locales, name in localesLabel:
            if locales == 'zh':
                ret['app_name'] = name
        if not ret.get('app_name'):
            applicationLabelRE = re.compile(r"application: label=\'(?P<app_name>[ \S]+)\' icon")
            ret['app_name'] = applicationLabelRE.search(app_info).group('app_name')

        # step5: 获取app的icon路径
        if iconInfo := re.compile(r"application: label=\'(?P<app_name>[ \S]+)\' icon=\'(?P<icon>\S+)\'").\
                search(app_info):
            ret['icon'] = iconInfo.group('icon')

        # step6: 获取app 启动的activity
        if launchableActivityInfo := re.compile(r'launchable-activity: name=\'(?P<launchable_activity>\S*)\'').\
                search(app_info):
            ret['launchable_activity'] = launchableActivityInfo.group('launchable_activity')

        return ret

    def _get_app_info(self, name: str) -> Optional[str]:
        app_path = self.device.get_app_install_path(name)
        # badging: Print the label and icon for the app declared in APK.
        if not app_path:
            raise AdbBaseError(f"'{name}' install path not found")

        ret = self.device.shell(f'{AAPT_REMOTE_PATH} d badging {app_path}')
        return ret

    def _get_app_path_list(self, flag_options: Union[None, str, list] = None) -> List[Tuple[str, str]]:
        """
        获取app的对应地址

        Args:
            flag_options: 获取app_list可指定参数,与pm list packages相同

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
