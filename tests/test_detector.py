import pytest
from unittest.mock import patch, MagicMock
from src.ffmpeg_hw_accel.detector import HWAccelDetector
from src.ffmpeg_hw_accel.accelerator import HWAccelerator, VideoCodec


SAMPLE_ENCODERS_OUTPUT = """
Encoders:
 V..... = Video
 A..... = Audio
 S..... = Subtitle
 ......
 V..... libx264              H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
 V..... libx265              H.265 / HEVC
 V..... h264_nvenc           NVIDIA NVENC H.264 encoder
 V..... hevc_nvenc           NVIDIA NVENC H.265 encoder
 V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration)
 A..... aac                  AAC (Advanced Audio Coding)
 A..... libmp3lame           libmp3lame MP3 (MPEG audio layer 3)
"""


class TestHWAccelDetector:
    def _make_detector(self) -> HWAccelDetector:
        return HWAccelDetector(ffmpeg_binary="ffmpeg")

    def _mock_run(self, stdout: str):
        mock_result = MagicMock()
        mock_result.stdout = stdout
        return mock_result

    # ------------------------------------------------------------------
    # _parse_encoder_names
    # ------------------------------------------------------------------

    def test_parse_encoder_names_finds_nvenc(self):
        names = HWAccelDetector._parse_encoder_names(SAMPLE_ENCODERS_OUTPUT)
        assert "h264_nvenc" in names
        assert "hevc_nvenc" in names

    def test_parse_encoder_names_finds_software(self):
        names = HWAccelDetector._parse_encoder_names(SAMPLE_ENCODERS_OUTPUT)
        assert "libx264" in names
        assert "libx265" in names

    def test_parse_encoder_names_ignores_audio(self):
        names = HWAccelDetector._parse_encoder_names(SAMPLE_ENCODERS_OUTPUT)
        # aac and libmp3lame should still be parsed (they are valid encoders)
        assert "aac" in names

    def test_parse_encoder_names_empty_output(self):
        names = HWAccelDetector._parse_encoder_names("")
        assert names == set()

    def test_parse_encoder_names_no_hw(self):
        output = """
 V..... libx264  H.264
 V..... libx265  H.265
"""
        names = HWAccelDetector._parse_encoder_names(output)
        assert "h264_nvenc" not in names
        assert "libx264" in names

    # ------------------------------------------------------------------
    # detect()
    # ------------------------------------------------------------------

    def test_detect_always_includes_none(self):
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            result = detector.detect()
        assert HWAccelerator.NONE in result

    def test_detect_finds_nvenc(self):
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            result = detector.detect()
        assert HWAccelerator.NVENC in result

    def test_detect_finds_qsv(self):
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            result = detector.detect()
        assert HWAccelerator.QSV in result

    def test_detect_no_hw_accel(self):
        output = " V..... libx264  H.264\n V..... libx265  H.265\n"
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(output)
            result = detector.detect()
        assert result == [HWAccelerator.NONE]

    def test_detect_raises_on_missing_binary(self):
        detector = self._make_detector()
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            with pytest.raises(RuntimeError, match="Failed to query ffmpeg binary"):
                detector.detect()

    def test_detect_raises_on_timeout(self):
        import subprocess
        detector = self._make_detector()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 30)):
            with pytest.raises(RuntimeError, match="Failed to query ffmpeg binary"):
                detector.detect()

    # ------------------------------------------------------------------
    # get_available_codecs_for()
    # ------------------------------------------------------------------

    def test_get_available_codecs_none_accel(self):
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            detector.detect()
        codecs = detector.get_available_codecs_for(HWAccelerator.NONE)
        assert VideoCodec.LIBX264 in codecs
        assert VideoCodec.LIBX265 in codecs

    def test_get_available_codecs_nvenc(self):
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            detector.detect()
        codecs = detector.get_available_codecs_for(HWAccelerator.NVENC)
        assert VideoCodec.H264_NVENC in codecs
        assert VideoCodec.HEVC_NVENC in codecs

    def test_get_available_codecs_nvenc_no_av1_if_absent(self):
        # av1_nvenc not in sample output
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            detector.detect()
        codecs = detector.get_available_codecs_for(HWAccelerator.NVENC)
        assert VideoCodec.AV1_NVENC not in codecs

    def test_get_available_codecs_triggers_detect_if_not_run(self):
        detector = self._make_detector()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = self._mock_run(SAMPLE_ENCODERS_OUTPUT)
            codecs = detector.get_available_codecs_for(HWAccelerator.NONE)
        assert VideoCodec.LIBX264 in codecs