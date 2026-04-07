from __future__ import annotations

import shlex
from typing import Any

from .accelerator import HWAccelerator, VideoCodec
from .compatibility import get_compatibility, AccelCompatibility
from .parser import FFmpegCommandParser, ParsedFFmpegCommand


class FFmpegCommandConverter:
    """
    Converts a parsed (or raw string) ffmpeg command to use a specific
    hardware accelerator.

    All operations are purely string/data transformations — no subprocess.
    """

    def __init__(self) -> None:
        self._parser = FFmpegCommandParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
            self,
            command: str,
            accel: HWAccelerator,
            fallback_on_no_codec: bool = True,
    ) -> str:
        """
        Convert *command* to use *accel*.

        Parameters
        ----------
        command:
            Original ffmpeg command string.
        accel:
            Target hardware accelerator.
        fallback_on_no_codec:
            If the original codec cannot be mapped for this accel, keep the
            original codec instead of raising.

        Returns
        -------
        str
            New ffmpeg command string with HW accel flags applied.
        """
        if accel == HWAccelerator.NONE:
            return command

        compat = get_compatibility(accel)
        parsed = self._parser.parse(command)
        tokens = list(parsed.tokens)

        tokens = self._remove_incompatible_flags(tokens, compat)
        tokens = self._convert_codecs(tokens, compat, fallback_on_no_codec)
        tokens = self._convert_presets(tokens, compat)
        tokens = self._convert_rate_control(tokens, compat)
        tokens = self._inject_input_flags(tokens, compat, parsed)
        tokens = self._inject_output_flags(tokens, compat, parsed)

        return shlex.join(tokens)

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    def _remove_incompatible_flags(
            self,
            tokens: list[str],
            compat: AccelCompatibility,
    ) -> list[str]:
        """Remove flags (and their arguments) that are incompatible with accel."""
        result: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            base_flag = tok.split(":")[0] if ":" in tok else tok
            if base_flag in compat.incompatible_flags or tok in compat.incompatible_flags:
                # Consume the flag's argument if next token is not a flag
                i += 1
                if i < len(tokens) and not tokens[i].startswith("-"):
                    i += 1
                continue
            result.append(tok)
            i += 1
        return result

    def _convert_codecs(
            self,
            tokens: list[str],
            compat: AccelCompatibility,
            fallback_on_no_codec: bool,
    ) -> list[str]:
        """Replace software video codec flags with HW codec equivalents."""
        result: list[str] = []
        i = 0
        codec_flags = {"-c:v", "-vcodec", "-c:v:0", "-codec:v"}
        while i < len(tokens):
            tok = tokens[i]
            # Match -c:v variants including stream specifiers
            is_codec_flag = (
                    tok in codec_flags
                    or (tok.startswith("-c:v") and len(tok) > 4)
                    or (tok.startswith("-codec:v"))
                    or (tok.startswith("-vcodec"))
            )
            if is_codec_flag and i + 1 < len(tokens):
                orig_codec_str = tokens[i + 1]
                try:
                    orig_codec = VideoCodec(orig_codec_str)
                    hw_codec = compat.codec_map.get(orig_codec)
                    if hw_codec is not None:
                        result.append(tok)
                        result.append(hw_codec.value)
                        i += 2
                        continue
                    elif not fallback_on_no_codec:
                        raise ValueError(
                            f"No HW codec mapping for '{orig_codec_str}' "
                            f"in accelerator '{compat}'"
                        )
                    # fallback: keep original
                except ValueError:
                    pass  # unknown codec string, keep as-is
            result.append(tok)
            i += 1
        return result

    def _convert_presets(
            self,
            tokens: list[str],
            compat: AccelCompatibility,
    ) -> list[str]:
        """Remap -preset values; drop if mapping is None."""
        result: list[str] = []
        i = 0
        preset_flags = {"-preset", "-preset:v"}
        while i < len(tokens):
            tok = tokens[i]
            if tok in preset_flags and i + 1 < len(tokens):
                orig_preset = tokens[i + 1]
                mapped = compat.preset_map.get(orig_preset)
                if mapped is None:
                    # Drop the -preset flag entirely
                    i += 2
                    continue
                result.append(tok)
                result.append(mapped)
                i += 2
                continue
            result.append(tok)
            i += 1
        return result

    def _convert_rate_control(
            self,
            tokens: list[str],
            compat: AccelCompatibility,
    ) -> list[str]:
        """
        Translate software rate-control flags (e.g. -crf) to HW equivalents.
        The value is preserved; only the flag name changes.
        """

        sw_rc_flags = {"-crf"}
        hw_rc_flag = compat.rc_flag

        if hw_rc_flag == "-crf":
            return tokens

        result: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in sw_rc_flags and i + 1 < len(tokens):
                result.append(hw_rc_flag)
                result.append(tokens[i + 1])
                i += 2
                continue
            result.append(tok)
            i += 1
        return result

    def _inject_input_flags(
            self,
            tokens: list[str],
            compat: AccelCompatibility,
            parsed: ParsedFFmpegCommand,
    ) -> list[str]:
        """
        Inject HW-specific flags before the first -i flag.
        Also removes any existing -hwaccel flags to avoid duplicates.
        """
        if not compat.extra_input_flags:
            return tokens

        # First, strip existing hwaccel flags
        clean: list[str] = []
        i = 0
        strip_flags = {"-hwaccel", "-hwaccel_device", "-hwaccel_output_format"}
        while i < len(tokens):
            tok = tokens[i]
            if tok in strip_flags and i + 1 < len(tokens):
                i += 2
                continue
            clean.append(tok)
            i += 1

        # Find position of first -i
        result: list[str] = []
        injected = False
        i = 0
        while i < len(clean):
            if clean[i] == "-i" and not injected:
                for flag, val in compat.extra_input_flags.items():
                    result.append(flag)
                    result.append(val)
                injected = True
            result.append(clean[i])
            i += 1

        return result

    def _inject_output_flags(
            self,
            tokens: list[str],
            compat: AccelCompatibility,
            parsed: ParsedFFmpegCommand,
    ) -> list[str]:
        """
        Inject HW-specific output flags before the output filename.
        Skips flags that are already present to avoid duplicates.
        """
        if not compat.extra_output_flags:
            return tokens

        # Determine output path(s)
        output_paths: set[str] = {
            o["path"] for o in parsed.outputs if o.get("path")
        }
        if not output_paths:
            return tokens

        existing_flags = set(tokens)
        new_flags: list[str] = [
            item
            for flag, val in compat.extra_output_flags.items()
            if flag not in existing_flags
            for item in (flag, val)
        ]
        if not new_flags:
            return tokens

        result: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in output_paths:
                result.extend(new_flags)
            result.append(tok)
            i += 1
        return result
