.PHONY: help dev test quality compile-linux compile-windows compile-android linux windows android

help:
	@echo 'make dev              Run the app from source'
	@echo 'make test             Run Python tests'
	@echo 'make quality          Run syntax, Ruff, tests, and coverage'
	@echo 'make compile-linux    Build the Linux AppImage on Linux'
	@echo 'make compile-windows  Build the Windows installer on Windows'
	@echo 'make compile-android  Build an Android arm64 APK on Linux'

ifeq ($(OS),Windows_NT)
dev:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/development/dev-windows.ps1
else
dev:
	bash scripts/development/dev.sh
endif

test:
	bash scripts/quality/test.sh

quality:
	bash scripts/quality/quality.sh

compile-linux linux:
	bash scripts/build/linux/build-linux.sh

compile-windows windows:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build/windows/build-windows.ps1

compile-android android:
	bash scripts/build/android/build-android.sh
