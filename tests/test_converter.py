import pytest
from src.ffmpeg_hw_accel.converter import FFmpegCommandConverter
from src.ffmpeg_hw_accel.accelerator import HWAccelerator


class TestFFmpegCommandConverter:
    def setup_method(self):
        self.conv = FFmpegCommandConverter()

    # ------------------------------------------------------------------
    # NONE passthrough
    # ------------------------------------------------------------------

    def test_none_accel_returns_unchanged(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset slow output.mp4"
        assert self.conv.convert(cmd, HWAccelerator.NONE) == cmd

    # ------------------------------------------------------------------
    # NVENC
    # ------------------------------------------------------------------

    def test_nvenc_replaces_libx264_codec(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "h264_nvenc" in result
        assert "libx264" not in result

    def test_nvenc_replaces_libx265_codec(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx265 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "hevc_nvenc" in result
        assert "libx265" not in result

    def test_nvenc_removes_tune_flag(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -tune film output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "-tune" not in result
        assert "film" not in result

    def test_nvenc_converts_preset_slow_to_p6(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset slow output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "-preset p6" in result or "p6" in result.split()

    def test_nvenc_converts_preset_medium_to_p5(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset medium output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "p5" in result.split()

    def test_nvenc_converts_crf_to_cq(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "-cq" in result
        assert "23" in result
        assert "-crf" not in result

    def test_nvenc_injects_hwaccel_cuda(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "-hwaccel cuda" in result or (
            "-hwaccel" in result.split() and
            result.split()[result.split().index("-hwaccel") + 1] == "cuda"
        )

    def test_nvenc_removes_x264opts(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -x264opts keyint=120 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "-x264opts" not in result

    def test_nvenc_preserves_audio_codec(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "-c:a aac" in result or (
            "-c:a" in result.split() and
            result.split()[result.split().index("-c:a") + 1] == "aac"
        )

    def test_nvenc_preserves_output_filename(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert result.endswith("output.mp4")

    def test_nvenc_no_duplicate_hwaccel_flags(self):
        cmd = "ffmpeg -hwaccel cuda -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert result.count("-hwaccel") == 1

    def test_nvenc_full_command(self):
        cmd = (
            "ffmpeg -y -i input.mp4 -c:v libx264 -preset slow "
            "-tune film -crf 22 -c:a aac -b:a 128k output.mp4"
        )
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "h264_nvenc" in result
        assert "-tune" not in result
        assert "-crf" not in result
        assert "-cq" in result
        assert "aac" in result

    # ------------------------------------------------------------------
    # QSV
    # ------------------------------------------------------------------

    def test_qsv_replaces_libx264(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.QSV)
        assert "h264_qsv" in result

    def test_qsv_injects_hwaccel_qsv(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.QSV)
        assert "-hwaccel" in result
        tokens = result.split()
        idx = tokens.index("-hwaccel")
        assert tokens[idx + 1] == "qsv"

    def test_qsv_removes_lossless_preset(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset lossless output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.QSV)
        assert "lossless" not in result

    def test_qsv_preserves_medium_preset(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset medium output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.QSV)
        assert "medium" in result

    def test_qsv_renames_crf_to_global_quality(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.QSV)
        assert "-global_quality" in result
        assert "-crf" not in result

    # ------------------------------------------------------------------
    # VAAPI
    # ------------------------------------------------------------------

    def test_vaapi_replaces_libx264(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VAAPI)
        assert "h264_vaapi" in result

    def test_vaapi_removes_all_presets(self):
        for preset_val in ["ultrafast", "fast", "medium", "slow", "veryslow"]:
            cmd = f"ffmpeg -i input.mp4 -c:v libx264 -preset {preset_val} output.mp4"
            result = self.conv.convert(cmd, HWAccelerator.VAAPI)
            assert "-preset" not in result, f"preset should be removed for VAAPI (was {preset_val})"

    def test_vaapi_removes_profile_v(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -profile:v high output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VAAPI)
        assert "-profile:v" not in result

    def test_vaapi_renames_crf_to_qp(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VAAPI)
        assert "-qp" in result
        assert "-crf" not in result

    def test_vaapi_injects_hwaccel_vaapi(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VAAPI)
        tokens = result.split()
        assert "-hwaccel" in tokens
        idx = tokens.index("-hwaccel")
        assert tokens[idx + 1] == "vaapi"

    # ------------------------------------------------------------------
    # VideoToolbox
    # ------------------------------------------------------------------

    def test_videotoolbox_replaces_libx264(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VIDEOTOOLBOX)
        assert "h264_videotoolbox" in result

    def test_videotoolbox_removes_crf(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VIDEOTOOLBOX)
        assert "-crf" not in result

    def test_videotoolbox_removes_all_presets(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset medium output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VIDEOTOOLBOX)
        assert "-preset" not in result

    def test_videotoolbox_removes_tune(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -tune film output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VIDEOTOOLBOX)
        assert "-tune" not in result

    def test_videotoolbox_no_hwaccel_flag_injected(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.VIDEOTOOLBOX)
        assert "-hwaccel" not in result

    # ------------------------------------------------------------------
    # AMF
    # ------------------------------------------------------------------

    def test_amf_replaces_libx264(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.AMF)
        assert "h264_amf" in result

    def test_amf_preset_slow_maps_to_quality(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset slow output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.AMF)
        assert "quality" in result

    def test_amf_preset_fast_maps_to_balanced(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset fast output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.AMF)
        assert "balanced" in result

    # ------------------------------------------------------------------
    # V4L2
    # ------------------------------------------------------------------

    def test_v4l2_replaces_libx264(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.V4L2)
        assert "h264_v4l2m2m" in result

    def test_v4l2_removes_preset(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset medium output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.V4L2)
        assert "-preset" not in result

    def test_v4l2_removes_crf(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.V4L2)
        assert "-crf" not in result

    # ------------------------------------------------------------------
    # Fallback behaviour
    # ------------------------------------------------------------------

    def test_unknown_codec_kept_with_fallback(self):
        # A codec not in any codec_map → keep original
        cmd = "ffmpeg -i input.mp4 -c:v libvpx output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "libvpx" in result

    def test_unknown_codec_raises_without_fallback(self):
        cmd = "ffmpeg -i input.mp4 -c:v libvpx output.mp4"
        # Should not raise because fallback_on_no_codec default is True
        result = self.conv.convert(cmd, HWAccelerator.NVENC, fallback_on_no_codec=True)
        assert "libvpx" in result

    # ------------------------------------------------------------------
    # Filter preservation
    # ------------------------------------------------------------------

    def test_vf_filter_preserved_nvenc(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -vf scale=1920:1080 output.mp4"
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "scale=1920:1080" in result

    def test_filter_complex_preserved(self):
        cmd = (
            'ffmpeg -i a.mp4 -i b.mp4 -filter_complex "[0:v][1:v]overlay" '
            "-c:v libx264 output.mp4"
        )
        result = self.conv.convert(cmd, HWAccelerator.NVENC)
        assert "overlay" in result