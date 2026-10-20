"""Single-gateway curation integration; leaves core Discord handlers untouched."""
from .main_gateway_bridge import wire


def register(ctx):
    ctx.register_platform_handler('discord', wire)
