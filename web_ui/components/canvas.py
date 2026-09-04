"""
FastHTML Component: Palette Canvas (SVG Wrapper)
"""
from fasthtml.common import *

def Canvas(svg_string: str):
    return Div(NotStr(svg_string), cls="svg-canvas")
