from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from .accelerator import HWAccelerator, VideoCodec, Preset, PixelFormat


@dataclass(frozen=True)
class AccelCompatibility:
    """
    Describes what is and is not compatible for a given HW accelerator.

    incompatible_flags  : flags that must be removed entirely
    preset_map          : maps unified Preset → native preset string (None = remove)
    pixel_format        : preferred pix_fmt to inject
    needs_hwaccel_flag  : whether -hwaccel <name> must be prepended to input
    hwaccel_init        : optional -init_hw_device string
    extra_input_flags   : extra flags to add before -i
    extra_output_flags  : extra flags to add to output
    codec_map           : maps software VideoCodec → HW VideoCodec
    supported_presets   : set of Preset values that are valid (empty = all)
    rc_flag             : rate-control flag name (e.g. "-cq", "-qp")
    """
    incompatible_flags: frozenset[str] = field(default_factory=frozenset)
    preset_map: dict[str, str | None] = field(default_factory=dict)
    pixel_format: PixelFormat | None = None
    needs_hwaccel_flag: bool = False
    hwaccel_init: str | None = None
    extra_input_flags: dict[str, str] = field(default_factory=dict)
    extra_output_flags: dict[str, str] = field(default_factory=dict)
    codec_map: dict[VideoCodec, VideoCodec] = field(default_factory=dict)
    supported_presets: frozenset[Preset] = field(default_factory=frozenset)
    rc_flag: str = "-crf"  # default sw flag; overridden per accel


# ---------------------------------------------------------------------------
# NVENC
# ---------------------------------------------------------------------------
_NVENC_PRESET_MAP: dict[str, str | None] = {
    Preset.ULTRAFAST.value: "p1",
    Preset.SUPERFAST.value: "p2",
    Preset.VERYFAST.value: "p3",
    Preset.FASTER.value: "p4",
    Preset.FAST.value: "p4",
    Preset.MEDIUM.value: "p5",
    Preset.SLOW.value: "p6",
    Preset.SLOWER.value: "p7",
    Preset.VERYSLOW.value: "p7",
    Preset.LOSSLESS.value: "lossless",
    Preset.LOSSLESSHP.value: "losslesshp",
    # NVENC does not support these → remove
    Preset.BALANCED.value: None,
    Preset.QUALITY.value: None,
}

_NVENC_SUPPORTED_PRESETS: frozenset[Preset] = frozenset({
    Preset.ULTRAFAST, Preset.SUPERFAST, Preset.VERYFAST,
    Preset.FASTER, Preset.FAST, Preset.MEDIUM,
    Preset.SLOW, Preset.SLOWER, Preset.VERYSLOW,
    Preset.LOSSLESS, Preset.LOSSLESSHP,
})

NVENC_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset({
        "-tune",           # libx264 tune has no NVENC equivalent
        "-x264opts",
        "-x264-params",
        "-x265-params",
    }),
    preset_map=_NVENC_PRESET_MAP,
    pixel_format=PixelFormat.NV12,
    needs_hwaccel_flag=True,
    extra_input_flags={"-hwaccel": "cuda"},
    extra_output_flags={"-rc:v": "vbr", "-b:v": "0"},
    codec_map={
        VideoCodec.LIBX264: VideoCodec.H264_NVENC,
        VideoCodec.LIBX265: VideoCodec.HEVC_NVENC,
    },
    supported_presets=_NVENC_SUPPORTED_PRESETS,
    rc_flag="-cq",
)

# ---------------------------------------------------------------------------
# QSV
# ---------------------------------------------------------------------------
_QSV_PRESET_MAP: dict[str, str | None] = {
    Preset.ULTRAFAST.value: "veryfast",
    Preset.SUPERFAST.value: "veryfast",
    Preset.VERYFAST.value: "veryfast",
    Preset.FASTER.value: "faster",
    Preset.FAST.value: "fast",
    Preset.MEDIUM.value: "medium",
    Preset.SLOW.value: "slow",
    Preset.SLOWER.value: "slower",
    Preset.VERYSLOW.value: "veryslow",
    Preset.BALANCED.value: "balanced",
    Preset.QUALITY.value: "slow",
    # Not applicable
    Preset.LOSSLESS.value: None,
    Preset.LOSSLESSHP.value: None,
}

_QSV_SUPPORTED_PRESETS: frozenset[Preset] = frozenset({
    Preset.VERYFAST, Preset.FASTER, Preset.FAST,
    Preset.MEDIUM, Preset.SLOW, Preset.SLOWER, Preset.VERYSLOW,
    Preset.BALANCED,
})

QSV_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset({
        "-tune", "-x264opts", "-x264-params", "-x265-params",
    }),
    preset_map=_QSV_PRESET_MAP,
    pixel_format=PixelFormat.NV12,
    needs_hwaccel_flag=True,
    extra_input_flags={"-hwaccel": "qsv", "-hwaccel_output_format": "qsv"},
    codec_map={
        VideoCodec.LIBX264: VideoCodec.H264_QSV,
        VideoCodec.LIBX265: VideoCodec.HEVC_QSV,
        VideoCodec.LIBVPX_VP9: VideoCodec.VP9_QSV,
    },
    supported_presets=_QSV_SUPPORTED_PRESETS,
    rc_flag="-global_quality",
)

# ---------------------------------------------------------------------------
# VAAPI
# ---------------------------------------------------------------------------
_VAAPI_PRESET_MAP: dict[str, str | None] = {
    # VAAPI has no preset concept → always remove
    Preset.ULTRAFAST.value: None,
    Preset.SUPERFAST.value: None,
    Preset.VERYFAST.value: None,
    Preset.FASTER.value: None,
    Preset.FAST.value: None,
    Preset.MEDIUM.value: None,
    Preset.SLOW.value: None,
    Preset.SLOWER.value: None,
    Preset.VERYSLOW.value: None,
    Preset.BALANCED.value: None,
    Preset.QUALITY.value: None,
    Preset.LOSSLESS.value: None,
    Preset.LOSSLESSHP.value: None,
}

VAAPI_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset({
        "-tune", "-x264opts", "-x264-params", "-x265-params",
        "-profile:v",   # VAAPI uses its own profile negotiation
    }),
    preset_map=_VAAPI_PRESET_MAP,
    pixel_format=PixelFormat.VAAPI,
    needs_hwaccel_flag=True,
    extra_input_flags={
        "-hwaccel": "vaapi",
        "-hwaccel_output_format": "vaapi",
    },
    extra_output_flags={"-vf": "format=nv12|vaapi,hwupload"},
    codec_map={
        VideoCodec.LIBX264: VideoCodec.H264_VAAPI,
        VideoCodec.LIBX265: VideoCodec.HEVC_VAAPI,
        VideoCodec.LIBVPX_VP9: VideoCodec.VP9_VAAPI,
    },
    supported_presets=frozenset(),   # none supported
    rc_flag="-qp",
)

# ---------------------------------------------------------------------------
# VideoToolbox (macOS)
# ---------------------------------------------------------------------------
_VTB_PRESET_MAP: dict[str, str | None] = {
    # VideoToolbox has no preset → remove all
    p.value: None for p in Preset
}

VIDEOTOOLBOX_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset({
        "-tune", "-x264opts", "-x264-params", "-x265-params",
        "-crf",          # VideoToolbox uses -q:v or -b:v
        "-profile:v",
    }),
    preset_map=_VTB_PRESET_MAP,
    pixel_format=PixelFormat.NV12,
    needs_hwaccel_flag=False,         # VTB is auto-selected via codec name
    codec_map={
        VideoCodec.LIBX264: VideoCodec.H264_VIDEOTOOLBOX,
        VideoCodec.LIBX265: VideoCodec.HEVC_VIDEOTOOLBOX,
    },
    supported_presets=frozenset(),
    rc_flag="-q:v",
)

# ---------------------------------------------------------------------------
# AMF (AMD)
# ---------------------------------------------------------------------------
_AMF_PRESET_MAP: dict[str, str | None] = {
    Preset.ULTRAFAST.value: "speed",
    Preset.SUPERFAST.value: "speed",
    Preset.VERYFAST.value: "speed",
    Preset.FASTER.value: "balanced",
    Preset.FAST.value: "balanced",
    Preset.MEDIUM.value: "balanced",
    Preset.SLOW.value: "quality",
    Preset.SLOWER.value: "quality",
    Preset.VERYSLOW.value: "quality",
    Preset.BALANCED.value: "balanced",
    Preset.QUALITY.value: "quality",
    Preset.LOSSLESS.value: None,
    Preset.LOSSLESSHP.value: None,
}

_AMF_SUPPORTED_PRESETS: frozenset[Preset] = frozenset({
    Preset.ULTRAFAST, Preset.SUPERFAST, Preset.VERYFAST,
    Preset.FASTER, Preset.FAST, Preset.MEDIUM,
    Preset.SLOW, Preset.SLOWER, Preset.VERYSLOW,
    Preset.BALANCED, Preset.QUALITY,
})

AMF_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset({
        "-tune", "-x264opts", "-x264-params", "-x265-params",
    }),
    preset_map=_AMF_PRESET_MAP,
    pixel_format=PixelFormat.NV12,
    needs_hwaccel_flag=False,
    codec_map={
        VideoCodec.LIBX264: VideoCodec.H264_AMF,
        VideoCodec.LIBX265: VideoCodec.HEVC_AMF,
    },
    supported_presets=_AMF_SUPPORTED_PRESETS,
    rc_flag="-qp_i",
)

# ---------------------------------------------------------------------------
# V4L2 M2M
# ---------------------------------------------------------------------------
V4L2_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset({
        "-tune", "-x264opts", "-x264-params", "-x265-params",
        "-preset", "-crf",
    }),
    preset_map={p.value: None for p in Preset},
    pixel_format=PixelFormat.NV12,
    needs_hwaccel_flag=False,
    codec_map={
        VideoCodec.LIBX264: VideoCodec.H264_V4L2M2M,
        VideoCodec.LIBX265: VideoCodec.HEVC_V4L2M2M,
    },
    supported_presets=frozenset(),
    rc_flag="-qp",
)

# ---------------------------------------------------------------------------
# NONE (software) — no transformations needed
# ---------------------------------------------------------------------------
NONE_COMPAT = AccelCompatibility(
    incompatible_flags=frozenset(),
    preset_map={p.value: p.value for p in Preset},
    pixel_format=None,
    needs_hwaccel_flag=False,
    codec_map={},
    supported_presets=frozenset(Preset),
    rc_flag="-crf",
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
COMPAT_REGISTRY: Final[dict[HWAccelerator, AccelCompatibility]] = {
    HWAccelerator.NONE:          NONE_COMPAT,
    HWAccelerator.NVENC:         NVENC_COMPAT,
    HWAccelerator.QSV:           QSV_COMPAT,
    HWAccelerator.VAAPI:         VAAPI_COMPAT,
    HWAccelerator.VIDEOTOOLBOX:  VIDEOTOOLBOX_COMPAT,
    HWAccelerator.AMF:           AMF_COMPAT,
    HWAccelerator.V4L2:          V4L2_COMPAT,
}


def get_compatibility(accel: HWAccelerator) -> AccelCompatibility:
    """Return the AccelCompatibility for the given accelerator."""
    return COMPAT_REGISTRY[accel]