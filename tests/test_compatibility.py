import pytest
from src.ffmpeg_hw_accel.compatibility import (
    get_compatibility, COMPAT_REGISTRY,
    NVENC_COMPAT, QSV_COMPAT, VAAPI_COMPAT,
    VIDEOTOOLBOX_COMPAT, AMF_COMPAT, V4L2_COMPAT, NONE_COMPAT,
)
from src.ffmpeg_hw_accel.accelerator import HWAccelerator, VideoCodec, Preset


class TestCompatRegistry:
    def test_all_accelerators_have_entry(self):
        for accel in HWAccelerator:
            assert accel in COMPAT_REGISTRY, f"Missing compat entry for {accel}"

    def test_get_compatibility_returns_correct_type(self):
        from src.ffmpeg_hw_accel.compatibility import AccelCompatibility
        for accel in HWAccelerator:
            compat = get_compatibility(accel)
            assert isinstance(compat, AccelCompatibility)


class TestNvencCompat:
    def test_tune_is_incompatible(self):
        assert "-tune" in NVENC_COMPAT.incompatible_flags

    def test_codec_map_libx264_to_h264_nvenc(self):
        assert NVENC_COMPAT.codec_map[VideoCodec.LIBX264] == VideoCodec.H264_NVENC

    def test_codec_map_libx265_to_hevc_nvenc(self):
        assert NVENC_COMPAT.codec_map[VideoCodec.LIBX265] == VideoCodec.HEVC_NVENC

    def test_preset_ultrafast_maps_to_p1(self):
        assert NVENC_COMPAT.preset_map[Preset.ULTRAFAST.value] == "p1"

    def test_preset_medium_maps_to_p5(self):
        assert NVENC_COMPAT.preset_map[Preset.MEDIUM.value] == "p5"

    def test_preset_veryslow_maps_to_p7(self):
        assert NVENC_COMPAT.preset_map[Preset.VERYSLOW.value] == "p7"

    def test_balanced_preset_removed(self):
        assert NVENC_COMPAT.preset_map[Preset.BALANCED.value] is None

    def test_hwaccel_flag_needed(self):
        assert NVENC_COMPAT.needs_hwaccel_flag is True

    def test_extra_input_flags_contain_cuda(self):
        assert NVENC_COMPAT.extra_input_flags.get("-hwaccel") == "cuda"

    def test_rc_flag_is_cq(self):
        assert NVENC_COMPAT.rc_flag == "-cq"


class TestQsvCompat:
    def test_tune_is_incompatible(self):
        assert "-tune" in QSV_COMPAT.incompatible_flags

    def test_codec_map_libx264_to_h264_qsv(self):
        assert QSV_COMPAT.codec_map[VideoCodec.LIBX264] == VideoCodec.H264_QSV

    def test_preset_medium_preserved(self):
        assert QSV_COMPAT.preset_map[Preset.MEDIUM.value] == "medium"

    def test_lossless_preset_removed(self):
        assert QSV_COMPAT.preset_map[Preset.LOSSLESS.value] is None

    def test_rc_flag_is_global_quality(self):
        assert QSV_COMPAT.rc_flag == "-global_quality"

    def test_hwaccel_output_format(self):
        assert QSV_COMPAT.extra_input_flags.get("-hwaccel_output_format") == "qsv"


class TestVaapiCompat:
    def test_all_presets_removed(self):
        for preset in Preset:
            assert VAAPI_COMPAT.preset_map.get(preset.value) is None

    def test_profile_v_is_incompatible(self):
        assert "-profile:v" in VAAPI_COMPAT.incompatible_flags

    def test_codec_map_libx264_to_h264_vaapi(self):
        assert VAAPI_COMPAT.codec_map[VideoCodec.LIBX264] == VideoCodec.H264_VAAPI

    def test_hwaccel_is_vaapi(self):
        assert VAAPI_COMPAT.extra_input_flags.get("-hwaccel") == "vaapi"

    def test_rc_flag_is_qp(self):
        assert VAAPI_COMPAT.rc_flag == "-qp"

    def test_supported_presets_empty(self):
        assert len(VAAPI_COMPAT.supported_presets) == 0


class TestVideotoolboxCompat:
    def test_all_presets_removed(self):
        for preset in Preset:
            assert VIDEOTOOLBOX_COMPAT.preset_map.get(preset.value) is None

    def test_crf_is_incompatible(self):
        assert "-crf" in VIDEOTOOLBOX_COMPAT.incompatible_flags

    def test_no_hwaccel_flag_needed(self):
        assert VIDEOTOOLBOX_COMPAT.needs_hwaccel_flag is False

    def test_codec_map_libx264(self):
        assert VIDEOTOOLBOX_COMPAT.codec_map[VideoCodec.LIBX264] == VideoCodec.H264_VIDEOTOOLBOX

    def test_rc_flag_is_qv(self):
        assert VIDEOTOOLBOX_COMPAT.rc_flag == "-q:v"


class TestAmfCompat:
    def test_codec_map_libx264(self):
        assert AMF_COMPAT.codec_map[VideoCodec.LIBX264] == VideoCodec.H264_AMF

    def test_preset_fast_maps_to_balanced(self):
        assert AMF_COMPAT.preset_map[Preset.FAST.value] == "balanced"

    def test_preset_slow_maps_to_quality(self):
        assert AMF_COMPAT.preset_map[Preset.SLOW.value] == "quality"

    def test_lossless_removed(self):
        assert AMF_COMPAT.preset_map[Preset.LOSSLESS.value] is None


class TestNoneCompat:
    def test_no_incompatible_flags(self):
        assert len(NONE_COMPAT.incompatible_flags) == 0

    def test_all_presets_preserved(self):
        for preset in Preset:
            mapped = NONE_COMPAT.preset_map.get(preset.value)
            assert mapped == preset.value

    def test_no_hwaccel_flag(self):
        assert NONE_COMPAT.needs_hwaccel_flag is False

    def test_all_sw_presets_supported(self):
        sw_presets = {
            Preset.ULTRAFAST, Preset.SUPERFAST, Preset.VERYFAST,
            Preset.FASTER, Preset.FAST, Preset.MEDIUM,
            Preset.SLOW, Preset.SLOWER, Preset.VERYSLOW,
        }
        for p in sw_presets:
            assert p in NONE_COMPAT.supported_presets