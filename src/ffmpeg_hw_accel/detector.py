from __future__ import annotations

import subprocess
import re
from typing import Final

from .accelerator import HWAccelerator, VideoCodec


# Maps accelerator → codec strings to probe for in `ffmpeg -encoders`
_ACCEL_PROBE_CODECS: Final[dict[HWAccelerator, list[str]]] = {
    HWAccelerator.NVENC:         ["h264_nvenc", "hevc_nvenc"],
    HWAccelerator.QSV:           ["h264_qsv", "hevc_qsv"],
    HWAccelerator.VAAPI:         ["h264_vaapi", "hevc_vaapi"],
    HWAccelerator.VIDEOTOOLBOX:  ["h264_videotoolbox", "hevc_videotoolbox"],
    HWAccelerator.AMF:           ["h264_amf", "hevc_amf"],
    HWAccelerator.V4L2:          ["h264_v4l2m2m"],
}


class HWAccelDetector:
    """
    Detects available hardware accelerators by querying the ffmpeg binary.
    All detection is done via subprocess; no GPU SDK is required.
    """

    def __init__(self, ffmpeg_binary: str = "ffmpeg") -> None:
        self._ffmpeg_binary: str = ffmpeg_binary
        self._available: list[HWAccelerator] | None = None
        self._available_codecs: set[str] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self) -> list[HWAccelerator]:
        """
        Run detection and return list of available HWAccelerator values.
        HWAccelerator.NONE (software) is always included.
        """
        self._available_codecs = self._get_encoder_list()
        result: list[HWAccelerator] = [HWAccelerator.NONE]

        for accel, probe_codecs in _ACCEL_PROBE_CODECS.items():
            if any(c in self._available_codecs for c in probe_codecs):
                result.append(accel)

        self._available = result
        return result

    def get_available_codecs_for(self, accel: HWAccelerator) -> list[VideoCodec]:
        """Return list of VideoCodec values available for a given accelerator."""
        if self._available_codecs is None:
            self.detect()

        codec_map: dict[HWAccelerator, list[VideoCodec]] = {
            HWAccelerator.NONE: [
                VideoCodec.LIBX264, VideoCodec.LIBX265,
                VideoCodec.LIBVPX_VP9, VideoCodec.LIBSVTAV1,
            ],
            HWAccelerator.NVENC: [
                VideoCodec.H264_NVENC, VideoCodec.HEVC_NVENC, VideoCodec.AV1_NVENC,
            ],
            HWAccelerator.QSV: [
                VideoCodec.H264_QSV, VideoCodec.HEVC_QSV,
                VideoCodec.AV1_QSV, VideoCodec.VP9_QSV,
            ],
            HWAccelerator.VAAPI: [
                VideoCodec.H264_VAAPI, VideoCodec.HEVC_VAAPI,
                VideoCodec.VP9_VAAPI, VideoCodec.AV1_VAAPI,
            ],
            HWAccelerator.VIDEOTOOLBOX: [
                VideoCodec.H264_VIDEOTOOLBOX, VideoCodec.HEVC_VIDEOTOOLBOX,
            ],
            HWAccelerator.AMF: [
                VideoCodec.H264_AMF, VideoCodec.HEVC_AMF, VideoCodec.AV1_AMF,
            ],
            HWAccelerator.V4L2: [
                VideoCodec.H264_V4L2M2M, VideoCodec.HEVC_V4L2M2M,
            ],
        }

        candidates = codec_map.get(accel, [])
        if accel == HWAccelerator.NONE:
            return candidates

        assert self._available_codecs is not None
        return [c for c in candidates if c.value in self._available_codecs]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_encoder_list(self) -> set[str]:
        """Call `ffmpeg -encoders` and return set of encoder names."""
        try:
            result = subprocess.run(
                [self._ffmpeg_binary, "-encoders", "-v", "quiet"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return self._parse_encoder_names(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            raise RuntimeError(
                f"Failed to query ffmpeg binary '{self._ffmpeg_binary}': {exc}"
            ) from exc

    @staticmethod
    def _parse_encoder_names(output: str) -> set[str]:
        """Parse encoder names from `ffmpeg -encoders` output."""
        names: set[str] = set()
        # Each encoder line looks like: " V..... h264_nvenc           ..."
        for line in output.splitlines():
            # Skip header lines
            if not line or line.startswith("=") or line.startswith(" -") or "Encoders" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and re.match(r"^[VAS.]+$", parts[0]):
                names.add(parts[1])
        return names