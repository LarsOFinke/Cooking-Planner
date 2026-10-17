[app]
title = Cooking Planner
package.name = cookingplanner
package.domain = org.cookingplanner
version = __PROJECT_VERSION__
source.dir = source
source.include_exts = py,json,csv,webp,png,jpg,jpeg
requirements = python3,kivy==2.3.1,sqlite3,libffi,openssl,sqlalchemy==2.0.30,android
orientation = portrait,landscape
fullscreen = 0
android.allow_backup = False
android.api = 36
android.minapi = 29
android.ndk = 29
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = develop
p4a.commit = 00aa709645ae871106207a1f4ac781d6042150b5
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
