import pytest
from ffmpeg_hw_accel.parser import FFmpegCommandParser, ParsedFFmpegCommand


class TestFFmpegCommandParser:
    def setup_method(self):
        self.parser = FFmpegCommandParser()

    # ------------------------------------------------------------------
    # Basic parsing
    # ------------------------------------------------------------------

    def test_parse_simple_command(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.ffmpeg_binary == "ffmpeg"
        assert parsed.inputs[0]["path"] == "input.mp4"
        assert parsed.outputs[0]["path"] == "output.mp4"

    def test_parse_video_codec_flag(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-c:v"] == "libx264"

    def test_parse_preset_flag(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset slow output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-preset"] == "slow"

    def test_parse_crf_flag(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-crf"] == "23"

    def test_parse_tune_flag(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -tune film output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-tune"] == "film"

    def test_parse_multiple_inputs(self):
        cmd = "ffmpeg -i a.mp4 -i b.mp4 -c:v libx264 output.mp4"
        parsed = self.parser.parse(cmd)
        assert len(parsed.inputs) == 2
        assert parsed.inputs[0]["path"] == "a.mp4"
        assert parsed.inputs[1]["path"] == "b.mp4"

    def test_parse_global_flags(self):
        cmd = "ffmpeg -y -i input.mp4 -c:v libx264 output.mp4"
        parsed = self.parser.parse(cmd)
        assert "-y" in parsed.global_options

    def test_parse_audio_codec(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -c:a aac output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-c:a"] == "aac"

    def test_parse_filter_complex(self):
        cmd = 'ffmpeg -i input.mp4 -vf "scale=1920:1080" output.mp4'
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-vf"] == "scale=1920:1080"

    def test_parse_video_bitrate(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -b:v 5M output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-b:v"] == "5M"

    def test_parse_tokens_preserved(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -preset slow output.mp4"
        parsed = self.parser.parse(cmd)
        assert "ffmpeg" in parsed.tokens
        assert "-preset" in parsed.tokens
        assert "slow" in parsed.tokens

    def test_parse_custom_binary(self):
        cmd = "/usr/local/bin/ffmpeg -i input.mp4 output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.ffmpeg_binary == "/usr/local/bin/ffmpeg"

    def test_parse_empty_command_raises(self):
        with pytest.raises(ValueError, match="Empty ffmpeg command"):
            self.parser.parse("")

    def test_parse_missing_i_argument_raises(self):
        with pytest.raises(ValueError):
            self.parser.parse("ffmpeg -i")

    def test_parse_hide_banner_flag(self):
        cmd = "ffmpeg -hide_banner -i input.mp4 output.mp4"
        parsed = self.parser.parse(cmd)
        assert "-hide_banner" in parsed.global_options

    def test_parse_pix_fmt(self):
        cmd = "ffmpeg -i input.mp4 -c:v libx264 -pix_fmt yuv420p output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-pix_fmt"] == "yuv420p"

    def test_parse_ss_flag(self):
        cmd = "ffmpeg -ss 00:00:10 -i input.mp4 output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.global_options.get("-ss") == "00:00:10"

    def test_parse_map_flag(self):
        cmd = "ffmpeg -i input.mp4 -map 0:v:0 -c:v libx264 output.mp4"
        parsed = self.parser.parse(cmd)
        assert parsed.outputs[0]["options"]["-map"] == "0:v:0"