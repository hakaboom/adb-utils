# -*- coding: utf-8 -*-
import os

STATICPATH = os.path.join(os.path.abspath('adbutils'), 'static')
DEFAULT_ADB_PATH = {
    "Windows": os.path.join(STATICPATH, "adb", "windows"),
    "Darwin": os.path.join(STATICPATH, "adb", "mac", "adb"),
    "Linux": os.path.join(STATICPATH, "adb", "linux", "adb"),
    "Linux-x86_64": os.path.join(STATICPATH, "adb", "linux", "adb"),
    "Linux-armv7l": os.path.join(STATICPATH, "adb", "linux_arm", "adb"),
}
ANDROID_ADB_SERVER_HOST = '127.0.0.1'
ANDROID_ADB_SERVER_PORT = 5037

ADB_CAP_REMOTE_PATH = '/data/local/tmp/screencap.raw'
ADB_CAP_LOCAL_PATH = './{device_id}.raw'

ADB_INSTALL_FAILED = {
    "INSTALL_FAILED_ALREADY_EXISTS": "应用已经存在，或卸载了但没卸载干净;建议使用'-r'安装",
    "INSTALL_FAILED_INVALID_APK": "无效的 APK 文件",
    "INSTALL_FAILED_INVALID_URI": "无效的 APK 文件名;确保 APK 文件名里无中文",
    "INSTALL_FAILED_INSUFFICIENT_STORAGE": "空间不足",
    "INSTALL_FAILED_DUPLICATE_PACKAGE": "已经存在同名程序",
    "INSTALL_FAILED_NO_SHARED_USER": "请求的共享用户不存在",
    "INSTALL_FAILED_UPDATE_INCOMPATIBLE": "以前安装过同名应用，但卸载时数据没有移除；或者已安装该应用，但签名不一致;先 adb uninstall",
    "INSTALL_FAILED_SHARED_USER_INCOMPATIBLE": "请求的共享用户存在但签名不一致",
    "INSTALL_FAILED_MISSING_SHARED_LIBRARY": "安装包使用了设备上不可用的共享库",
    "INSTALL_FAILED_REPLACE_COULDNT_DELETE": "替换时无法删除",
    "INSTALL_FAILED_DEXOPT": "dex 优化验证失败或空间不足",
    "INSTALL_FAILED_OLDER_SDK": "设备系统版本低于应用要求",
    "INSTALL_FAILED_CONFLICTING_PROVIDER": "设备里已经存在与应用里同名的 content provider",
    "INSTALL_FAILED_NEWER_SDK": "设备系统版本高于应用要求",
    "INSTALL_FAILED_TEST_ONLY": "应用是 test-only 的，但安装时没有指定 -t 参数",
    "INSTALL_FAILED_CPU_ABI_INCOMPATIBLE": "包含不兼容设备 CPU 应用程序二进制接口的 native code",
    "INSTALL_FAILED_MISSING_FEATURE": "应用使用了设备不可用的功能",
    "INSTALL_FAILED_CONTAINER_ERROR": "1. sdcard 访问失败;2. 应用签名与 ROM 签名一致，被当作内置应用。",
    "INSTALL_FAILED_INVALID_INSTALL_LOCATION": "1. 不能安装到指定位置;2. 应用签名与 ROM 签名一致，被当作内置应用。",
    "INSTALL_FAILED_MEDIA_UNAVAILABLE": "安装位置不可用",
    "INSTALL_FAILED_VERIFICATION_TIMEOUT": "验证安装包超时",
    "INSTALL_FAILED_VERIFICATION_FAILURE": "验证安装包失败",
    "INSTALL_FAILED_PACKAGE_CHANGED": "应用与调用程序期望的不一致",
    "INSTALL_FAILED_UID_CHANGED": "以前安装过该应用，与本次分配的 UID 不一致",
    "INSTALL_FAILED_VERSION_DOWNGRADE": "已经安装了该应用更高版本",
    "INSTALL_FAILED_PERMISSION_MODEL_DOWNGRADE": "已安装 target SDK 支持运行时权限的同名应用，要安装的版本不支持运行时权限",
    "INSTALL_PARSE_FAILED_NOT_APK": "指定路径不是文件，或不是以 .apk 结尾",
    "INSTALL_PARSE_FAILED_BAD_MANIFEST": "无法解析的 AndroidManifest.xml 文件",
    "INSTALL_PARSE_FAILED_UNEXPECTED_EXCEPTION": "解析器遇到异常",
    "INSTALL_PARSE_FAILED_NO_CERTIFICATES": "安装包没有签名",
    "INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES": "已安装该应用，且签名与 APK 文件不一致",
    "INSTALL_PARSE_FAILED_CERTIFICATE_ENCODING": "解析 APK 文件时遇到 CertificateEncodingException",
    "INSTALL_PARSE_FAILED_BAD_PACKAGE_NAME": "manifest 文件里没有或者使用了无效的包名",
    "INSTALL_PARSE_FAILED_BAD_SHARED_USER_ID": "manifest 文件里指定了无效的共享用户 ID",
    "INSTALL_PARSE_FAILED_MANIFEST_MALFORMED": "解析 manifest 文件时遇到结构性错误",
    "INSTALL_PARSE_FAILED_MANIFEST_EMPTY": "在 manifest 文件里找不到找可操作标签（instrumentation 或 application）",
    "INSTALL_FAILED_INTERNAL_ERROR": "因系统问题安装失败",
    "INSTALL_FAILED_USER_RESTRICTED": "用户被限制安装应用",
    "INSTALL_FAILED_DUPLICATE_PERMISSION": "应用尝试定义一个已经存在的权限名称",
    "INSTALL_FAILED_NO_MATCHING_ABIS": "应用包含设备的应用程序二进制接口不支持的 native code",
    "INSTALL_CANCELED_BY_USER": "应用安装需要在设备上确认，但未操作设备或点了取消",
    "INSTALL_FAILED_ACWF_INCOMPATIBLE": "应用程序与设备不兼容",
    "does not contain AndroidManifest.xml": "无效的 APK 文件",
    "is not a valid zip file": "无效的 APK 文件",
    "Offline": "设备未连接成功",
    "unauthorized": "设备未授权允许调试",
    "error: device not found": "没有连接成功的设备",
    "protocol failure": "设备已断开连接",
    "Unknown option: -s": "Android 2.2 以下不支持安装到 sdcard",
    "No space left on device": "空间不足",
    "Permission denied … sdcard …": "sdcard 不可用",
    "signatures do not match the previously installed version; ignoring!": "已安装该应用且签名不一致",
}
