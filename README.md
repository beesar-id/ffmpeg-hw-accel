# ffmpeg-hw-accel

A Python library that converts standard (software) `ffmpeg` commands into hardware-accelerated equivalents, automatically detecting available accelerators on the current machine and handling all compatibility differences between encoders.

> **The library only transforms command strings. Executing the command is always left to the caller.**

---

## Table of Contents

- [Features](#features)
- [Supported Hardware Accelerators](#supported-hardware-accelerators)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [Initialisation](#initialisation)
  - [Detecting Available Accelerators](#detecting-available-accelerators)
  - [Converting a Command](#converting-a-command)
  - [Fallback Behaviour](#fallback-behaviour)
  - [Executing the Converted Command](#executing-the-converted-command)
  - [Selecting the Best Available Accelerator](#selecting-the-best-available-accelerator)
  - [Resetting the Singleton](#resetting-the-singleton)
- [Compatibility Rules](#compatibility-rules)
- [Development](#development)
  - [Setup](#setup)
  - [Running Tests](#running-tests)

---

## Features

- 🔍 **Auto-detection**: queries your local `ffmpeg` binary at startup to discover which hardware encoders are actually available
- 🔄 **Command conversion**: rewrites `-c:v`, `-preset`, `-crf`, `-tune`, and other flags to their hardware-accelerated equivalents
- 🛡️ **Compatibility enforcement**: automatically removes flags that are incompatible with the chosen accelerator (e.g. `-tune` has no meaning for NVENC)
- ↩️ **Automatic fallback**: if the target accelerator is unavailable or conversion fails, the original command is returned unchanged (configurable)
- 🏗️ **Singleton design**: one instance per process; detection runs once at initialisation
- 🔒 **Strict typing**: all parameters use enums; no magic strings internally
- 🌍 **Cross-platform**: works on Linux, Windows, and macOS; available accelerators depend on the hardware present

---

## Supported Hardware Accelerators

| Accelerator | Enum | Typical Platform | Example Codecs |
|---|---|---|---|
| Software (fallback) | `HWAccelerator.NONE` | All | `libx264`, `libx265` |
| NVIDIA NVENC | `HWAccelerator.NVENC` | Windows, Linux | `h264_nvenc`, `hevc_nvenc` |
| Intel Quick Sync | `HWAccelerator.QSV` | Windows, Linux | `h264_qsv`, `hevc_qsv` |
| AMD AMF | `HWAccelerator.AMF` | Windows, Linux | `h264_amf`, `hevc_amf` |
| VAAPI | `HWAccelerator.VAAPI` | Linux | `h264_vaapi`, `hevc_vaapi` |
| Apple VideoToolbox | `HWAccelerator.VIDEOTOOLBOX` | macOS | `h264_videotoolbox`, `hevc_videotoolbox` |
| V4L2 M2M | `HWAccelerator.V4L2` | Linux (Raspberry Pi) | `h264_v4l2m2m` |

---

## Requirements

- Python **3.11+**
- `ffmpeg` installed and accessible on your `PATH` (or provide the full path)
- The hardware driver and SDK corresponding to the accelerator you want to use (e.g. NVIDIA drivers for NVENC)

---

## Installation

```bash
pip install ffmpeg-hw-accel
```

Or with `uv`:

```bash
uv add ffmpeg-hw-accel
```

---

## Quick Start

```python
from ffmpeg_hw_accel import FFmpegHWAccel, HWAccelerator

# Initialise — detects available hardware at this point
accel = FFmpegHWAccel.get_instance()

# See what was found
print(accel.available_accelerators)
# [<HWAccelerator.NONE: 'none'>, <HWAccelerator.NVENC: 'nvenc'>]

# Convert a command
original = "ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 22 -c:a aac output.mp4"
converted = accel.convert(original, HWAccelerator.NVENC)

print(converted)
# ffmpeg -hwaccel cuda -i input.mp4 -c:v h264_nvenc -preset p6 -cq 22 -c:a aac -rc:v vbr -b:v 0 output.mp4
```

---

## Usage Guide

### Initialisation

`FFmpegHWAccel` is a **singleton**. The first call to `get_instance()` creates the instance and runs hardware detection. All subsequent calls return the same object.

```python
from ffmpeg_hw_accel import FFmpegHWAccel

# Default — uses "ffmpeg" from PATH, fallback enabled
accel = FFmpegHWAccel.get_instance()

# Custom ffmpeg binary
accel = FFmpegHWAccel.get_instance(
    ffmpeg_binary="/usr/local/bin/ffmpeg",  # full path or name on PATH
    auto_fallback=True,                      # True = return original on any error (default)
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `ffmpeg_binary` | `str` | `"ffmpeg"` | Path or name of the ffmpeg executable |
| `auto_fallback` | `bool` | `True` | Return the original command unchanged if conversion fails or the accelerator is unavailable |

---

### Detecting Available Accelerators

```python
# Full list
print(accel.available_accelerators)
# [<HWAccelerator.NONE: 'none'>, <HWAccelerator.NVENC: 'nvenc'>]

# Check a specific accelerator
accel.is_available(HWAccelerator.NVENC)         # True
accel.is_available(HWAccelerator.VIDEOTOOLBOX)  # False (not macOS)

# List codecs available for a given accelerator
codecs = accel.get_available_codecs(HWAccelerator.NVENC)
# [<VideoCodec.H264_NVENC: 'h264_nvenc'>, <VideoCodec.HEVC_NVENC: 'hevc_nvenc'>]
```

---

### Converting a Command

Pass any standard ffmpeg command string and a target `HWAccelerator`:

```python
original = (
    "ffmpeg -i input.mp4 "
    "-c:v libx264 -preset medium -tune film -crf 23 "
    "-c:a aac -b:a 192k output.mp4"
)

# NVENC
print(accel.convert(original, HWAccelerator.NVENC))
# ffmpeg -hwaccel cuda -i input.mp4
#   -c:v h264_nvenc -preset p5 -cq 23
#   -c:a aac -b:a 192k -rc:v vbr -b:v 0 output.mp4
# (-tune film removed — not supported by NVENC)

# QSV
print(accel.convert(original, HWAccelerator.QSV))
# ffmpeg -hwaccel qsv -hwaccel_output_format qsv -i input.mp4
#   -c:v h264_qsv -preset medium -global_quality 23
#   -c:a aac -b:a 192k output.mp4

# VAAPI (Linux)
print(accel.convert(original, HWAccelerator.VAAPI))
# ffmpeg -hwaccel vaapi -hwaccel_output_format vaapi -i input.mp4
#   -c:v h264_vaapi -qp 23
#   -c:a aac -b:a 192k -vf format=nv12|vaapi,hwupload output.mp4
# (-preset and -tune removed — VAAPI has no preset concept)

# VideoToolbox (macOS)
print(accel.convert(original, HWAccelerator.VIDEOTOOLBOX))
# ffmpeg -i input.mp4
#   -c:v h264_videotoolbox -q:v 23
#   -c:a aac -b:a 192k output.mp4
# (-preset, -tune, -crf all removed — not supported)

# AMF (AMD)
print(accel.convert(original, HWAccelerator.AMF))
# ffmpeg -i input.mp4
#   -c:v h264_amf -preset balanced -qp_i 23
#   -c:a aac -b:a 192k output.mp4
```

---

### Fallback Behaviour

#### `auto_fallback=True` (default)

The original command is returned unchanged when:
- The requested accelerator is **not detected** on the machine
- An **exception** occurs during conversion

```python
accel = FFmpegHWAccel.get_instance(auto_fallback=True)
cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"

# VAAPI not available on this machine → returns original silently
result = accel.convert(cmd, HWAccelerator.VAAPI)
print(result)
# "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
```

#### `auto_fallback=False`

Raises exceptions instead of silently falling back:

```python
from ffmpeg_hw_accel import FFmpegHWAccel, HWAccelerator

FFmpegHWAccel.reset_instance()
accel = FFmpegHWAccel.get_instance(auto_fallback=False)
cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"

try:
    result = accel.convert(cmd, HWAccelerator.VAAPI)
except ValueError as e:
    print(e)
    # Hardware accelerator 'vaapi' is not available on this machine.
    # Available: ['none', 'nvenc']
```

---

### Executing the Converted Command

The library only produces a command string. Running it is your responsibility:

```python
import subprocess
import shlex
from ffmpeg_hw_accel import FFmpegHWAccel, HWAccelerator

accel = FFmpegHWAccel.get_instance()
original = "ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 22 output.mp4"
hw_cmd = accel.convert(original, HWAccelerator.NVENC)

try:
    subprocess.run(shlex.split(hw_cmd), check=True)
    print("Encoding complete.")
except subprocess.CalledProcessError as e:
    print(f"Hardware encoding failed: {e}")
    # Manually fall back to software
    subprocess.run(shlex.split(original), check=True)
```

---

### Selecting the Best Available Accelerator

```python
from ffmpeg_hw_accel import FFmpegHWAccel, HWAccelerator

def get_best_accel(accel: FFmpegHWAccel) -> HWAccelerator:
    preference = [
        HWAccelerator.NVENC,
        HWAccelerator.QSV,
        HWAccelerator.VIDEOTOOLBOX,
        HWAccelerator.AMF,
        HWAccelerator.VAAPI,
        HWAccelerator.V4L2,
        HWAccelerator.NONE,   # software fallback — always available
    ]
    return next(a for a in preference if accel.is_available(a))


accel = FFmpegHWAccel.get_instance()
best = get_best_accel(accel)

original = "ffmpeg -i input.mp4 -c:v libx264 -preset medium -crf 23 -c:a aac output.mp4"
final_cmd = accel.convert(original, best)

print(f"Selected: {best.value}")
print(f"Command:  {final_cmd}")
```

---

### Resetting the Singleton

Useful when you need to switch `ffmpeg` binary or re-run detection (e.g. in tests):

```python
FFmpegHWAccel.reset_instance()

# Next call creates a fresh instance with new detection
accel = FFmpegHWAccel.get_instance(ffmpeg_binary="/opt/homebrew/bin/ffmpeg")
```

---

## Compatibility Rules

The table below summarises what each accelerator removes or transforms:

| Flag | NVENC | QSV | VAAPI | VideoToolbox | AMF | V4L2 |
|---|---|---|---|---|---|---|
| `-tune` | ❌ removed | ❌ removed | ❌ removed | ❌ removed | ❌ removed | ❌ removed |
| `-x264opts` | ❌ removed | ❌ removed | ❌ removed | ❌ removed | ❌ removed | ❌ removed |
| `-x264-params` | ❌ removed | ❌ removed | ❌ removed | ❌ removed | ❌ removed | ❌ removed |
| `-preset` | ✏️ remapped (p1–p7) | ✏️ remapped | ❌ removed | ❌ removed | ✏️ remapped | ❌ removed |
| `-crf` | ✏️ → `-cq` | ✏️ → `-global_quality` | ✏️ → `-qp` | ❌ removed | ✏️ → `-qp_i` | ❌ removed |
| `-profile:v` | ✅ kept | ✅ kept | ❌ removed | ❌ removed | ✅ kept | ✅ kept |
| `-c:v libx264` | ✏️ → `h264_nvenc` | ✏️ → `h264_qsv` | ✏️ → `h264_vaapi` | ✏️ → `h264_videotoolbox` | ✏️ → `h264_amf` | ✏️ → `h264_v4l2m2m` |
| `-c:v libx265` | ✏️ → `hevc_nvenc` | ✏️ → `hevc_qsv` | ✏️ → `hevc_vaapi` | ✏️ → `hevc_videotoolbox` | ✏️ → `hevc_amf` | ✏️ → `hevc_v4l2m2m` |

---

## Development

### Setup

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-username/ffmpeg-hw-accel.git
cd ffmpeg-hw-accel

# Install dependencies including dev extras
uv sync --extra dev
```

### Running Tests

```bash
# Run all tests
uv run pytest

# With coverage report
uv run pytest --cov=src/ffmpeg_hw_accel --cov-report=term-missing

# Run a specific test file
uv run pytest tests/test_converter.py

# Run a specific test case
uv run pytest tests/test_converter.py::TestFFmpegCommandConverter::test_nvenc_replaces_libx264_codec

# Verbose output
uv run pytest -v
```