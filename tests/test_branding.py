"""Shared wordmark rendering, colour and narrow-terminal contracts."""

import importlib
import importlib.util
import io
import xml.etree.ElementTree as ET

from rich.console import Console


def branding():
    assert importlib.util.find_spec('openwfn.branding') is not None, 'Shared branding is missing'
    return importlib.import_module('openwfn.branding')


def test_wide_terminal_renders_pixel_wordmark_and_subtitle(monkeypatch):
    monkeypatch.delenv('NO_COLOR', raising=False)
    stream = io.StringIO()
    branding().print_welcome(Console(file=stream, width=80, force_terminal=True, color_system='standard'))
    output = stream.getvalue()
    assert '▄▀▀▄' in output
    assert 'Wavefunction analysis toolkit' in output
    assert '\x1b[' in output


def test_narrow_terminal_uses_readable_name_without_wrapping():
    stream = io.StringIO()
    branding().print_welcome(Console(file=stream, width=28, force_terminal=False))
    output = stream.getvalue()
    assert 'openWFN' in output
    assert '▄▀▀▄' not in output
    assert '\x1b' not in output
    assert all(len(line) <= 28 for line in output.splitlines())


def test_no_colour_respects_console_configuration():
    stream = io.StringIO()
    branding().print_welcome(Console(file=stream, width=80, force_terminal=True, no_color=True))
    assert '\x1b[' not in stream.getvalue()


def test_svg_wordmark_has_font_independent_pixels_and_bounded_geometry():
    root = ET.fromstring(branding().wordmark_svg())
    ns = '{http://www.w3.org/2000/svg}'
    assert root.find(f'{ns}title').text == 'openWFN'
    assert root.findall(f'{ns}image') == []
    assert root.findall(f'{ns}text') == []
    pixels = root.findall(f'{ns}rect')
    assert len(pixels) > 80
    assert {pixel.attrib['fill'] for pixel in pixels} == {'#e5edf1', '#43d9e8', '#11171b'}
    for pixel in pixels:
        assert float(pixel.attrib['x']) + float(pixel.attrib['width']) <= 560
        assert float(pixel.attrib['y']) + float(pixel.attrib['height']) <= 120


def test_small_icon_is_one_legible_cyan_initial_not_squeezed_full_name():
    root = ET.fromstring(branding().icon_svg())
    assert root.attrib['viewBox'] == '0 0 32 32'
    pixels = root.findall('{http://www.w3.org/2000/svg}rect')
    assert len(pixels) > 10
    assert all(pixel.attrib['fill'] == '#43d9e8' for pixel in pixels)
