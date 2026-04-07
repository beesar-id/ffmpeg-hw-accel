from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FFmpegStream:
    """Represents a single output stream mapping in an ffmpeg command."""
    stream_specifier: str | None = None   # e.g. "0:v", "0:a"
    video_codec: str | None = None        # value of -c:v
    audio_codec: str | None = None        # value of -c:a
    video_options: dict[str, str] = field(default_factory=dict)
    audio_options: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedFFmpegCommand:
    """
    Structured representation of a parsed ffmpeg command.

    All token positions are preserved so the converter can
    perform surgical replacements without destroying unrelated flags.
    """
    ffmpeg_binary: str = "ffmpeg"
    global_options: dict[str, str | None] = field(default_factory=dict)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    # Flat ordered token list for reconstruction
    tokens: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Flags that take NO argument (boolean flags)
# ---------------------------------------------------------------------------
_BOOL_FLAGS: frozenset[str] = frozenset({
    "-y", "-n", "-nostdin", "-nostats", "-progress",
    "-hide_banner", "-ignore_unknown", "-copy_unknown",
    "-benchmark", "-benchmark_all", "-dump", "-hex",
    "-re", "-accurate_seek", "-noaccurate_seek",
    "-copyts", "-start_at_zero", "-shortest",
})

# ---------------------------------------------------------------------------
# Flags that consume one argument
# ---------------------------------------------------------------------------
_ARG_FLAGS: frozenset[str] = frozenset({
    "-i", "-f", "-c", "-c:v", "-c:a", "-c:s",
    "-vcodec", "-acodec", "-scodec",
    "-preset", "-tune", "-profile:v", "-profile",
    "-b:v", "-b:a", "-minrate", "-maxrate", "-bufsize",
    "-crf", "-cq", "-qp", "-qmin", "-qmax",
    "-r", "-s", "-vf", "-af", "-filter_complex",
    "-pix_fmt", "-aspect",
    "-t", "-ss", "-to", "-fs",
    "-vn", "-an", "-sn",
    "-map", "-map_metadata", "-map_chapters",
    "-threads", "-thread_queue_size",
    "-movflags", "-fflags",
    "-metadata", "-metadata:s:v", "-metadata:s:a",
    "-level", "-g", "-keyint_min",
    "-rc", "-rc-lookahead", "-surfaces", "-delay",
    "-hwaccel", "-hwaccel_device", "-hwaccel_output_format",
    "-init_hw_device", "-filter_hw_device",
    "-vaapi_device",
    "-global_quality",
    "-look_ahead", "-look_ahead_depth",
    "-usage", "-quality",
})


class FFmpegCommandParser:
    """
    Parses a flat ffmpeg command string into a structured representation.

    Strategy:
    - Tokenise with shlex.split (handles quoted paths correctly).
    - Walk tokens left-to-right tracking position relative to -i flags.
    - Preserve original token list for faithful reconstruction.
    """

    def parse(self, command: str) -> ParsedFFmpegCommand:
        tokens = shlex.split(command)
        if not tokens:
            raise ValueError("Empty ffmpeg command")

        parsed = ParsedFFmpegCommand(
            ffmpeg_binary=tokens[0],
            tokens=tokens,
        )

        i = 1
        current_input: dict[str, Any] | None = None
        current_output: dict[str, Any] | None = None
        seen_input = False

        while i < len(tokens):
            tok = tokens[i]

            # ----------------------------------------------------------------
            # Input file
            # ----------------------------------------------------------------
            if tok == "-i":
                i += 1
                if i >= len(tokens):
                    raise ValueError("'-i' flag without argument")
                current_input = {"path": tokens[i], "options": {}}
                parsed.inputs.append(current_input)
                seen_input = True
                i += 1
                # Start accumulating output options after last -i
                current_output = {"path": None, "options": {}}
                continue

            # ----------------------------------------------------------------
            # Boolean flags
            # ----------------------------------------------------------------
            if tok in _BOOL_FLAGS:
                if not seen_input:
                    parsed.global_options[tok] = None
                elif current_output is not None:
                    current_output["options"][tok] = None
                i += 1
                continue

            # ----------------------------------------------------------------
            # Flags with one argument
            # ----------------------------------------------------------------
            if tok in _ARG_FLAGS or self._is_stream_flag(tok):
                i += 1
                if i >= len(tokens):
                    break
                val = tokens[i]
                if not seen_input:
                    parsed.global_options[tok] = val
                else:
                    if current_output is not None:
                        current_output["options"][tok] = val
                i += 1
                continue

            # ----------------------------------------------------------------
            # Last positional token after inputs → output path
            # ----------------------------------------------------------------
            if seen_input and not tok.startswith("-"):
                if current_output is None:
                    current_output = {"path": None, "options": {}}
                current_output["path"] = tok
                parsed.outputs.append(current_output)
                current_output = {"path": None, "options": {}}
                i += 1
                continue

            # ----------------------------------------------------------------
            # Unknown flags — store as global or output option
            # ----------------------------------------------------------------
            if tok.startswith("-"):
                # Peek ahead: if next token is also a flag or end, treat as bool
                next_tok = tokens[i + 1] if i + 1 < len(tokens) else None
                if next_tok is None or next_tok.startswith("-"):
                    if not seen_input:
                        parsed.global_options[tok] = None
                    elif current_output is not None:
                        current_output["options"][tok] = None
                    i += 1
                else:
                    if not seen_input:
                        parsed.global_options[tok] = next_tok
                    elif current_output is not None:
                        current_output["options"][tok] = next_tok
                    i += 2
                continue

            i += 1

        return parsed

    @staticmethod
    def _is_stream_flag(flag: str) -> bool:
        """
        Detect stream-specifier variants like -c:v:0, -b:a:1, -preset:v, etc.
        These always take one argument.
        """
        base_flags = {
            "-c", "-codec", "-b", "-q", "-profile",
            "-preset", "-tune", "-filter", "-metadata",
        }
        parts = flag.split(":")
        return parts[0] in base_flags and len(parts) > 1