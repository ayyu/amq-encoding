__all__ = [
  'vp9_settings',
  'resolutions',
  'probe_dimensions',
  'encode_webm'
]


from os import devnull

from fractions import Fraction
import subprocess
from typing import Dict

import ffmpeg

from . import common


vp9_settings = {
  'c:v': 'libvpx-vp9',
  'b:v': 0,
  'g': 119,
  'crf': 20,
  'pix_fmt': 'yuv420p',
  'deadline': 'good',
  'cpu-used': 1,
  'row-mt': 1,
  'frame-parallel': 0,
  'tile-columns': 2,
  'tile-rows': 0,
  'threads': 4
}
"""(dict of str: str/int): Default VP9 parameters."""

resolutions = [0, 360, 480, 720]
"""(list of int): Default set of resolutions to encode."""

init_vf = {
  'scale': 1,
  'setsar': 1
}
"""(dict of str: int): Initial video filters to be used.
Includes SAR of 1:1.
"""


def probe_dimensions(input_file: str) -> Dict[str, any]:
  """
  Returns a dict of dimensional info for the input file.

  Args:
    input_file (str): Path to video file to probe.

  Returns:
    (dict of str: int/Fraction):
      Dictionary containing dimensional info of probed file.
      Includes keys `width`, `height`, `sar`, and `dar`.
      Defaults of `sar` = 1 and `dar` = `width`/`height` if not found in file.
  """
  metadata = ffmpeg.probe(input_file, select_streams='v')['streams'][0]
  return {
    'width': int(metadata['width']),
    'height': int(metadata['height']),
    'sar': Fraction(metadata.get(
      'sample_aspect_ratio',
      '1:1').replace(':', '/')),
    'dar': Fraction(metadata.get(
      'display_aspect_ratio',
      '{w}:{h}'.format(w=metadata['width'], h=metadata['height'])
      ).replace(':', '/'))
    }


def encode_webm(
    input_file: str,
    output_file: str,
    **kwargs) -> None:
  """
  Encodes a webm from the supplied input file. Uses 2-pass VP9 encoding.

  Args:
    input_file (str): Path to video file to encode from.
    output_file (str): Path to output encoded file.
    **kwargs: Arbitrary keyword arguments. Includes arguments specific to this
      package, as well as any native ffmpeg parameters you wish to pass.

  Keyword Args:
    vf (str or dict of str: str/None):
      String or dictionary of video filters to apply.
    af (str or dict of str: str/None):
      String or dictionary of audio filters to apply.
  """

  input = ffmpeg.input(input_file)
  audio = common.apply_filters(input.audio,
    common.parse_filter_string(kwargs.pop('af', {})))
  video = common.apply_filters(input.video,
    common.parse_filter_string(kwargs.pop('vf', {})))

  seek = common.extract_seek(kwargs)
  pass_1_cmd = ffmpeg.output(
    video,
    devnull, format='null',
    **dict({'pass': 1}, **kwargs)).compile()
  pass_2_cmd = ffmpeg.output(
    audio, video,
    output_file, format='webm',
    **dict({'pass': 2}, **kwargs)).compile()
  if not len(seek) == 0:
    pass_1_cmd[1:1] = seek
    pass_2_cmd[1:1] = seek
  subprocess.run(pass_1_cmd)
  subprocess.run(pass_2_cmd)
