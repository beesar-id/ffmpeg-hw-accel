from enum import Enum, auto


class HWAccelerator(str, Enum):
    """Supported hardware accelerators."""
    NONE = "none"                  # Software fallback (libx264/libx265)
    NVENC = "nvenc"                # NVIDIA GPU (Windows/Linux)
    QSV = "qsv"                    # Intel Quick Sync Video (Windows/Linux)
    VAAPI = "vaapi"                # Video Acceleration API (Linux only)
    VIDEOTOOLBOX = "videotoolbox"  # Apple VideoToolbox (macOS only)
    AMF = "amf"                    # AMD AMF (Windows/Linux)
    V4L2 = "v4l2m2m"              # V4L2 M2M (Linux/Raspberry Pi)


class VideoCodec(str, Enum):
    """Video codec identifiers used in ffmpeg -c:v."""
    # Software
    LIBX264 = "libx264"
    LIBX265 = "libx265"
    LIBVPX_VP9 = "libvpx-vp9"
    LIBSVTAV1 = "libsvtav1"
    # NVENC
    H264_NVENC = "h264_nvenc"
    HEVC_NVENC = "hevc_nvenc"
    AV1_NVENC = "av1_nvenc"
    # QSV
    H264_QSV = "h264_qsv"
    HEVC_QSV = "hevc_qsv"
    AV1_QSV = "av1_qsv"
    VP9_QSV = "vp9_qsv"
    # VAAPI
    H264_VAAPI = "h264_vaapi"
    HEVC_VAAPI = "hevc_vaapi"
    VP9_VAAPI = "vp9_vaapi"
    AV1_VAAPI = "av1_vaapi"
    # VideoToolbox
    H264_VIDEOTOOLBOX = "h264_videotoolbox"
    HEVC_VIDEOTOOLBOX = "hevc_videotoolbox"
    # AMF
    H264_AMF = "h264_amf"
    HEVC_AMF = "hevc_amf"
    AV1_AMF = "av1_amf"
    # V4L2
    H264_V4L2M2M = "h264_v4l2m2m"
    HEVC_V4L2M2M = "hevc_v4l2m2m"


class AudioCodec(str, Enum):
    """Audio codec identifiers."""
    AAC = "aac"
    MP3 = "libmp3lame"
    OPUS = "libopus"
    VORBIS = "libvorbis"
    AC3 = "ac3"
    EAC3 = "eac3"
    COPY = "copy"
    FLAC = "flac"
    PCM_S16LE = "pcm_s16le"


class Preset(str, Enum):
    """
    Unified preset names. Each HW accel maps these to its native preset.
    Not all presets are valid for all accelerators — see compatibility.py.
    """
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"
    # NVENC-specific
    LOSSLESS = "lossless"
    LOSSLESSHP = "losslesshp"
    # QSV / AMF abstract names
    BALANCED = "balanced"
    QUALITY = "quality"


class PixelFormat(str, Enum):
    """Common pixel formats used in -pix_fmt."""
    YUV420P = "yuv420p"
    YUV444P = "yuv444p"
    NV12 = "nv12"
    P010LE = "p010le"
    CUDA = "cuda"
    VAAPI = "vaapi"
    QSV = "qsv"
    VIDEOTOOLBOX_DEFAULT = "nv12"  # VideoToolbox default output


class TuneOption(str, Enum):
    """Tune options for libx264/libx265 (not compatible with HW accel)."""
    FILM = "film"
    ANIMATION = "animation"
    GRAIN = "grain"
    STILLIMAGE = "stillimage"
    FASTDECODE = "fastdecode"
    ZEROLATENCY = "zerolatency"
    PSNR = "psnr"
    SSIM = "ssim"


class RateControlMode(str, Enum):
    """Rate control modes (translated per accelerator)."""
    CRF = "crf"        # Constant Rate Factor (software)
    CQP = "cqp"        # Constant Quantization Parameter (HW)
    CBR = "cbr"        # Constant Bitrate
    VBR = "vbr"        # Variable Bitrate
    CONSTQP = "constqp"