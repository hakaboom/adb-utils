# -*- coding: utf-8 -*-
from adbutils import ADBDevice
from adbutils._utils import split_cmd
from adbutils.constant import (AAPT_LOCAL_PATH, AAPT_REMOTE_PATH, ANDROID_TMP_PATH,
                               BUSYBOX_REMOTE_PATH, BUSYBOX_LOCAL_PATH,
                               AAPT2_LOCAL_PATH, AAPT2_REMOTE_PATH)
from adbutils.exceptions import AdbBaseError
from loguru import logger

from typing import Union, Tuple, List, Optional, Match, Dict
import re
import os
import time


class Apk(object):
    ICON_DIR_NAME = 'icon'

    def __init__(self, device: ADBDevice, packageName: str):
        self.device = device

        self._install_aapt2()
        self._install_busyBox()

        self.device.check_dir(path=ANDROID_TMP_PATH, name=self.ICON_DIR_NAME, flag=True)
        self.app_info = self._dump_app_info(packageName)

    @property
    def packageName(self) -> str:
        """
        解析获取apk包名

        Returns:
            包名
        """
        if info := re.compile(r'package: name=\'(?P<package_name>\S*)\' ').search(self.app_info):
            return info.group('package_name')

    @property
    def name(self) -> str:
        """
        解析获取apk的label名

        Returns:
            apk名
        """
        if info := re.compile(r"application-label-(\S*):\'([ \S]+)\'").findall(self.app_info):
            for locales, name in info:
                if locales in ('zh', 'zh-CN', 'zh-HK'):
                    return name
        if info := re.compile(r"application: label=\'(?P<app_name>[ \S]+)\' icon").search(self.app_info):
            return info.group('app_name')

    @property
    def version_code(self) -> str:
        """
        解析获取apk的版本号

        Returns:
            版本号
        """
        if info := re.compile(r'versionCode=\'(?P<versionCode>\S*)\' ').search(self.app_info):
            return info.group('versionCode')

    @property
    def version_name(self) -> str:
        """
        解析获取apk的版本名

        Returns:
            版本名
        """
        if info := re.compile(r'versionName=\'(?P<versionName>[ \S]+)\' ').search(self.app_info):
            return info.group('versionName')

    @property
    def main_activity(self) -> str:
        """
        解析获取apk的主activity

        Returns:
            主activity
        """
        if info := re.compile(r'launchable-activity: name=\'(?P<launchable_activity>\S*)\'').search(self.app_info):
            return info.group('launchable_activity')

    @property
    def sdk_version(self) -> str:
        """
        解析获取apk的sdk版本号

        Returns:
            sdk版本号
        """
        if info := re.compile(r'sdkVersion:\'(?P<sdkVersion>\d+)\'').search(self.app_info):
            return info.group('sdkVersion')

    @property
    def target_sdk_version(self) -> str:
        """
        解析获取apk的目标sdk版本号

        Returns:
            目标sdk版本号
        """
        if info := re.compile(r'targetSdkVersion:\'(?P<targetSdkVersion>\d+)\'').search(self.app_info):
            return info.group('targetSdkVersion')

    @property
    def platformBuildVersionName(self) -> str:
        """
        解析获取apk的构建平台版本名

        Returns:
            构建平台版本名
        """
        if info := re.compile(r'platformBuildVersionName=\'(?P<platformBuildVersionName>\S*)\'').search(self.app_info):
            return info.group('platformBuildVersionName')

    @property
    def icon_info(self) -> str:
        """
        解析获取apk的icon文件信息

        Returns:
            icon文件信息
        """
        if info := re.compile(r'application-icon-(\S*):\'(?P<icon>\S+)\'').findall(self.app_info):
            return info[-1][-1]

    @property
    def install_path(self) -> str:
        return self.device.get_app_install_path(self.packageName)

    def _dump_icon_from_androidManifest(self):
        xml = self.aapt_shell(['dump', 'xmltree', self.install_path, '--file', 'AndroidManifest.xml'])
        pattern = re.compile('E: application.*icon\(\S+\)=@(?P<id>\S+)', re.DOTALL)
        if m := pattern.search(xml):
            return self._dump_path_from_resources(m.group('id'))

    def _dump_path_from_resources(self, _id: str):
        resources = self.aapt_shell(['dump resources', self.install_path])
        pattern = re.compile(f'resource {_id}(.+?)resource', re.DOTALL)
        if m := pattern.search(resources):
            resource = m.group(1)
            resFileRE = re.compile('\((\S+dpi)\).* [\"\']?(\S+\.png)')
            if icon_file := resFileRE.findall(resource):
                return icon_file[-1][-1]

        return None

    def get_icon_file(self, local: str) -> None:
        """
        获取icon文件到本地<local>

        Args:
            local: 需要保存到的路径

        Returns:
            None
        """
        icon_info = self.icon_info
        if os.path.splitext(icon_info)[-1] == '.xml':
            icon_info = self._dump_icon_from_androidManifest()

        save_dir = os.path.join(ANDROID_TMP_PATH, f'{self.ICON_DIR_NAME}/')
        save_path = os.path.join(save_dir, self.packageName)
        # step1: 检查保存路径下是否存在包名路径
        self.device.check_dir(save_dir, name=self.packageName, flag=True)

        # step2: 解压缩base.apk里的icon文件,保存到save_path下
        self.device.shell(cmds=[BUSYBOX_REMOTE_PATH, 'unzip', '-oq', self.install_path,
                                f"\"{icon_info}\"", '-d', save_path])
        time.sleep(.2)

        # step3: 将save_path下的png文件,pull到本地
        pull_path = os.path.join(f'{save_path}/', icon_info)
        self.device.pull(remote=pull_path, local=local)

    def _install_aapt(self) -> None:
        """
        check if appt installed

        Returns:
            None
        """
        if not self.device.check_file(ANDROID_TMP_PATH, 'aapt'):
            aapt_local_path = AAPT_LOCAL_PATH.format(abi_version=self.device.abi_version)
            self.device.push(local=aapt_local_path, remote=AAPT_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', AAPT_REMOTE_PATH])

    def _install_aapt2(self):
        if not self.device.check_file(ANDROID_TMP_PATH, 'aapt2'):
            aapt2_local_path = AAPT2_LOCAL_PATH.format(abi_version=self.device.abi_version)
            self.device.push(local=aapt2_local_path, remote=AAPT2_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', AAPT2_REMOTE_PATH])

    def _install_busyBox(self) -> None:
        """
        check if busyBox installed

        Returns:
            None
        """
        if not self.device.check_file(ANDROID_TMP_PATH, 'busybox'):
            if 'v8' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v8l')
            elif 'v7r' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v7r')
            elif 'v7m' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v7m')
            elif 'v7l' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v7l')
            elif 'v5' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v5l')
            else:
                local = BUSYBOX_LOCAL_PATH.format('v8l')

            self.device.push(local=local, remote=BUSYBOX_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', BUSYBOX_REMOTE_PATH])

    def _dump_app_info(self, packageName: str) -> str:
        app_path = self.device.get_app_install_path(packageName)
        if not app_path:
            raise AdbBaseError(f"'{packageName}' install path not found")

        return self.aapt_shell(f'd badging {app_path}')

    def aapt_shell(self, cmds: Union[list, str]):
        cmds = [f'{AAPT2_REMOTE_PATH}'] + split_cmd(cmds)
        return self.device.shell(cmds)

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
