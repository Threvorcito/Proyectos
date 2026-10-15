import secrets

from django import template
from django.utils.html import json_script

from homework.decoding import decode_map as build_decode_map

register = template.Library()


@register.simple_tag
def decode_map(text):
    return json_script(build_decode_map(text), f'decode-map-{secrets.token_hex(4)}')
