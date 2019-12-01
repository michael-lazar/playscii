# dict for key shift-char mappings

import sdl2

# MAYBE-TODO: find out if this breaks for non-US english KB layouts

SHIFT_MAP = {
    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%', '6': '^', '7': '&', '8': '*',
    '9': '(', '0': ')', '-': '_', '=': '+', '`': '~', '[': '{', ']': '}', '\\': '|',
    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
}

NUMLOCK_ON_MAP = {
    sdl2.SDLK_KP_0: sdl2.SDLK_0,
    sdl2.SDLK_KP_1: sdl2.SDLK_1,
    sdl2.SDLK_KP_2: sdl2.SDLK_2,
    sdl2.SDLK_KP_3: sdl2.SDLK_3,
    sdl2.SDLK_KP_4: sdl2.SDLK_4,
    sdl2.SDLK_KP_5: sdl2.SDLK_5,
    sdl2.SDLK_KP_6: sdl2.SDLK_6,
    sdl2.SDLK_KP_7: sdl2.SDLK_7,
    sdl2.SDLK_KP_8: sdl2.SDLK_8,
    sdl2.SDLK_KP_9: sdl2.SDLK_9,
    sdl2.SDLK_KP_DIVIDE: sdl2.SDLK_SLASH,
    sdl2.SDLK_KP_MULTIPLY: sdl2.SDLK_ASTERISK,
    sdl2.SDLK_KP_PLUS: sdl2.SDLK_PLUS,
    sdl2.SDLK_KP_MINUS: sdl2.SDLK_MINUS,
    sdl2.SDLK_KP_PERIOD: sdl2.SDLK_PERIOD,
    sdl2.SDLK_KP_ENTER: sdl2.SDLK_RETURN
}

NUMLOCK_OFF_MAP = {
    sdl2.SDLK_KP_0: sdl2.SDLK_INSERT,
    sdl2.SDLK_KP_1: sdl2.SDLK_END,
    sdl2.SDLK_KP_2: sdl2.SDLK_DOWN,
    sdl2.SDLK_KP_3: sdl2.SDLK_PAGEDOWN,
    sdl2.SDLK_KP_4: sdl2.SDLK_LEFT,
    sdl2.SDLK_KP_6: sdl2.SDLK_RIGHT,
    sdl2.SDLK_KP_7: sdl2.SDLK_HOME,
    sdl2.SDLK_KP_8: sdl2.SDLK_UP,
    sdl2.SDLK_KP_9: sdl2.SDLK_PAGEUP,
    sdl2.SDLK_KP_PERIOD: sdl2.SDLK_DELETE,
    sdl2.SDLK_KP_ENTER: sdl2.SDLK_RETURN
}
