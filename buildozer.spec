[app]

# 应用基本信息
title = 通信网络题库答题系统
package.name = quizsystem
package.domain = com.quizsystem
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

# 入口文件
main.py = main.py

# 版本信息
version = 1.0.0
version.code = 1

# 应用要求
requirements = python3,kivy==2.3.1,openpyxl==3.1.5,pillow
# NDK/SDK 版本（稳定兼容组合）
android.ndk = 25b
android.api = 33
android.minapi = 24
android.ndk_api = 24
android.gradle_dependencies = 
orientation = portrait

# 权限
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET

# 全屏/状态栏
fullscreen = 0
android.statusbar_color = 1E293B
android.navbar_color = 1E293B

# 日志级别
log_level = 2

# 架构（arm64-v8a 兼容 99% 现代手机）
android.archs = arm64-v8a
android.accept_sdk_license = True

# SDK / NDK 路径（使用 GitHub Actions 预装环境，避免下载和许可证问题）
android.sdk_path = /home/runner/android-sdk
android.ndk_path = /home/runner/android-sdk/ndk/25.1.8937393

# 图标和启动图
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png

# 签名（发布时需要修改）
# android.release = release
# p4a.branch = develop

# 复制数据目录
source.include_patterns = data/*.json,data/*.xlsx

[buildozer]

# 构建依赖
log_level = 2
warn_on_root = 1
