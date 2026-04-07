import pytest
from unittest.mock import patch, MagicMock
from src.ffmpeg_hw_accel.singleton import FFmpegHWAccel
from src.ffmpeg_hw_accel.accelerator import HWAccelerator


MINIMAL_ENCODERS = (
    " V..... libx264  H.264\n"
    " V..... h264_nvenc  NVIDIA NVENC\n"
    " V..... hevc_nvenc  NVIDIA NVENC HEVC\n"
)


def _mock_subprocess(stdout: str = MINIMAL_ENCODERS):
    mock_result = MagicMock()
    mock_result.stdout = stdout
    return patch("subprocess.run", return_value=mock_result)


class TestFFmpegHWAccelSingleton:
    def setup_method(self):
        FFmpegHWAccel.reset_instance()

    def teardown_method(self):
        FFmpegHWAccel.reset_instance()

    # ------------------------------------------------------------------
    # Singleton behaviour
    # ------------------------------------------------------------------

    def test_get_instance_returns_same_object(self):
        with _mock_subprocess():
            a = FFmpegHWAccel.get_instance()
            b = FFmpegHWAccel.get_instance()
        assert a is b

    def test_reset_creates_new_instance(self):
        with _mock_subprocess():
            a = FFmpegHWAccel.get_instance()
        FFmpegHWAccel.reset_instance()
        with _mock_subprocess():
            b = FFmpegHWAccel.get_instance()
        assert a is not b

    def test_direct_instantiation_is_possible(self):
        # __init__ is not private — power users can still instantiate directly
        with _mock_subprocess():
            inst = FFmpegHWAccel(ffmpeg_binary="ffmpeg")
        assert inst is not None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_available_accelerators_always_includes_none(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert HWAccelerator.NONE in inst.available_accelerators

    def test_available_accelerators_includes_nvenc(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert HWAccelerator.NVENC in inst.available_accelerators

    def test_available_accelerators_returns_copy(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        lst = inst.available_accelerators
        lst.append(HWAccelerator.AMF)
        assert HWAccelerator.AMF not in inst.available_accelerators

    def test_ffmpeg_binary_default(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert inst.ffmpeg_binary == "ffmpeg"

    def test_ffmpeg_binary_custom(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel(ffmpeg_binary="/opt/ffmpeg/bin/ffmpeg")
        assert inst.ffmpeg_binary == "/opt/ffmpeg/bin/ffmpeg"

    def test_auto_fallback_default_true(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert inst.auto_fallback is True

    def test_auto_fallback_can_be_disabled(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel(auto_fallback=False)
        assert inst.auto_fallback is False

    # ------------------------------------------------------------------
    # is_available()
    # ------------------------------------------------------------------

    def test_is_available_none_always_true(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert inst.is_available(HWAccelerator.NONE) is True

    def test_is_available_nvenc_true(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert inst.is_available(HWAccelerator.NVENC) is True

    def test_is_available_vaapi_false_when_absent(self):
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert inst.is_available(HWAccelerator.VAAPI) is False

    # ------------------------------------------------------------------
    # convert() — fallback behaviour
    # ------------------------------------------------------------------

    def test_convert_with_available_accel(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        result = inst.convert(cmd, HWAccelerator.NVENC)
        assert "h264_nvenc" in result

    def test_convert_unavailable_accel_fallback(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance(auto_fallback=True)
        result = inst.convert(cmd, HWAccelerator.VAAPI)
        # VAAPI not available → returns original
        assert result == cmd

    def test_convert_unavailable_accel_raises_when_no_fallback(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        with _mock_subprocess():
            inst = FFmpegHWAccel(auto_fallback=False)
        with pytest.raises(ValueError, match="not available"):
            inst.convert(cmd, HWAccelerator.VAAPI)

    def test_convert_none_accel_returns_original(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance()
        assert inst.convert(cmd, HWAccelerator.NONE) == cmd

    def test_convert_exception_fallback(self):
        """If converter raises, auto_fallback returns original command."""
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        with _mock_subprocess():
            inst = FFmpegHWAccel.get_instance(auto_fallback=True)

        with patch.object(inst._converter, "convert", side_effect=RuntimeError("boom")):
            result = inst.convert(cmd, HWAccelerator.NVENC)
        assert result == cmd

    def test_convert_exception_raises_when_no_fallback(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        with _mock_subprocess():
            inst = FFmpegHWAccel(auto_fallback=False)

        with patch.object(inst._converter, "convert", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="Conversion to"):
                inst.convert(cmd, HWAccelerator.NVENC)