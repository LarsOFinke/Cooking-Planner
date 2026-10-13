[app]
title = Cooking Planner
package.name = cookingplanner
package.domain = org.cookingplanner
version = 0.1.0
source.dir = source
source.include_exts = py,json,csv,webp,png,jpg,jpeg
requirements = python3,kivy,sqlite3,libffi,openssl,sqlalchemy==2.0.30,pydantic-core==2.41.4,pydantic==2.12.3,fastapi==0.115.14,uvicorn,android
orientation = portrait,landscape
fullscreen = 0
android.permissions = INTERNET
android.api = 36
android.minapi = 29
android.ndk = 29
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = develop
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
