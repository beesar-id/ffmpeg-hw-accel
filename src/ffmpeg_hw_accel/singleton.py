from __future__ import annotations

import threading
from typing import ClassVar

from .accelerator import HWAccelerator, VideoCodec
from .detector import HWAccelDetector
from .converter import FFmpegCommandConverter


class FFmpegHWAccel:
    """
    Singleton facade for the ffmpeg HW acceleration library.

    Usage
    -----
    ::

        accel = FFmpegHWAccel.get_instance()
        # or with options:
        accel = FFmpegHWAccel.get_instance(
            ffmpeg_binary="/usr/local/bin/ffmpeg",
            auto_fallback=True,
        )

        available = accel.available_accelerators
        cmd = accel.convert(
            "ffmpeg -i in.mp4 -c:v libx264 -preset slow -crf 23 out.mp4",
            HWAccelerator.NVENC,
        )
    """

    _instance: ClassVar[FFmpegHWAccel | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        ffmpeg_binary: str = "ffmpeg",
        auto_fallback: bool = True,
    ) -> None:
        """
        Do not call directly — use ``FFmpegHWAccel.get_instance()``.
        """
        self._ffmpeg_binary: str = ffmpeg_binary
        self._auto_fallback: bool = auto_fallback
        self._detector = HWAccelDetector(ffmpeg_binary=ffmpeg_binary)
        self._converter = FFmpegCommandConverter()
        # Run detection eagerly at init time
        self._available: list[HWAccelerator] = self._detector.detect()

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(
        cls,
        ffmpeg_binary: str = "ffmpeg",
        auto_fallback: bool = True,
    ) -> "FFmpegHWAccel":
        """
        Return the singleton instance, creating it on first call.

        Parameters
        ----------
        ffmpeg_binary:
            Path or name of the ffmpeg binary. Defaults to ``"ffmpeg"``.
        auto_fallback:
            If ``True`` (default), :meth:`convert` returns the original
            command unchanged when conversion raises an error.
            If ``False``, the error is re-raised.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        ffmpeg_binary=ffmpeg_binary,
                        auto_fallback=auto_fallback,
                    )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Destroy the current singleton instance.
        Primarily useful in tests to force re-initialisation.
        """
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available_accelerators(self) -> list[HWAccelerator]:
        """List of HWAccelerator values detected on this machine."""
        return list(self._available)

    @property
    def ffmpeg_binary(self) -> str:
        """The ffmpeg binary path used by this instance."""
        return self._ffmpeg_binary

    @property
    def auto_fallback(self) -> bool:
        """Whether automatic fallback to original command is enabled."""
        return self._auto_fallback

    def is_available(self, accel: HWAccelerator) -> bool:
        """Return ``True`` if *accel* was detected on this machine."""
        return accel in self._available

    def get_available_codecs(self, accel: HWAccelerator) -> list[VideoCodec]:
        """Return available VideoCodec values for *accel*."""
        return self._detector.get_available_codecs_for(accel)

    def convert(
        self,
        command: str,
        accel: HWAccelerator,
    ) -> str:
        """
        Convert *command* to use *accel*.

        If *accel* is not available on this machine, raises ``ValueError``
        (or falls back if ``auto_fallback=True``).

        If conversion fails and ``auto_fallback=True``, the original
        *command* is returned unchanged.

        Parameters
        ----------
        command:
            Original ffmpeg command string (software-encoded).
        accel:
            The hardware accelerator to target.

        Returns
        -------
        str
            Converted ffmpeg command string.

        Raises
        ------
        ValueError
            If *accel* is not available and ``auto_fallback=False``.
        RuntimeError
            If conversion fails and ``auto_fallback=False``.
        """
        if not self.is_available(accel):
            msg = (
                f"Hardware accelerator '{accel.value}' is not available "
                f"on this machine. Available: "
                f"{[a.value for a in self._available]}"
            )
            if self._auto_fallback:
                return command
            raise ValueError(msg)

        try:
            return self._converter.convert(command, accel)
        except Exception as exc:
            if self._auto_fallback:
                return command
            raise RuntimeError(
                f"Conversion to '{accel.value}' failed: {exc}"
            ) from exc