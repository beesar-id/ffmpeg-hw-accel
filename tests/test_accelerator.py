import pytest
from src.ffmpeg_hw_accel.accelerator import (
    HWAccelerator, VideoCodec, AudioCodec, Preset, PixelFormat,
    TuneOption, RateControlMode,
)


class TestHWAccelerator:
    def test_all_values_are_strings(self):
        for member in HWAccelerator:
            assert isinstance(member.value, str)

    def test_none_value(self):
        assert HWAccelerator.NONE.value == "none"

    def test_nvenc_value(self):
        assert HWAccelerator.NVENC.value == "nvenc"

    def test_from_string(self):
        assert HWAccelerator("nvenc") == HWAccelerator.NVENC
        assert HWAccelerator("vaapi") == HWAccelerator.VAAPI

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            HWAccelerator("nonexistent_accel")

    def test_all_members_present(self):
        expected = {"none", "nvenc", "qsv", "vaapi", "videotoolbox", "amf", "v4l2m2m"}
        actual = {m.value for m in HWAccelerator}
        assert expected == actual


class TestVideoCodec:
    def test_software_codecs_present(self):
        assert VideoCodec.LIBX264.value == "libx264"
        assert VideoCodec.LIBX265.value == "libx265"

    def test_nvenc_codecs_present(self):
        assert VideoCodec.H264_NVENC.value == "h264_nvenc"
        assert VideoCodec.HEVC_NVENC.value == "hevc_nvenc"
        assert VideoCodec.AV1_NVENC.value == "av1_nvenc"

    def test_vaapi_codecs_present(self):
        assert VideoCodec.H264_VAAPI.value == "h264_vaapi"

    def test_from_string(self):
        assert VideoCodec("libx264") == VideoCodec.LIBX264


class TestPreset:
    def test_software_presets(self):
        sw = {
            Preset.ULTRAFAST, Preset.SUPERFAST, Preset.VERYFAST,
            Preset.FASTER, Preset.FAST, Preset.MEDIUM,
            Preset.SLOW, Preset.SLOWER, Preset.VERYSLOW,
        }
        for p in sw:
            assert isinstance(p.value, str)

    def test_nvenc_presets(self):
        assert Preset.LOSSLESS.value == "lossless"
        assert Preset.LOSSLESSHP.value == "losslesshp"