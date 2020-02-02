
import random

# wildflowers palette ramp definitions

PALETTE_RAMPS = {
    # palette name : list of its ramps
    'dpaint': [
        # ramp tuple: (start index, length, stride)
        # generally, lighter / more vivid to darker
        (17, 16, 1),  # white to black
        (33, 16, 1),  # red to black
        (49, 8, 1),   # white to red
        (57, 8, 1),   # light orange to dark orange
        (65, 16, 1),  # light yellow to ~black
        (81, 8, 1),   # light green to green
        (89, 24, 1),  # white to green to ~black
        (113, 16, 1), # light cyan to ~black
        (129, 8, 1),  # light blue to blue
        (137, 24, 1), # white to blue to ~black
        (161, 16, 1), # light purple to ~black
        (177, 16, 1), # light magenta to ~black
        (193, 24, 1), # pale flesh to ~black
        (225, 22, 1)  # ROYGBV rainbow
    ],
    'doom': [
        (17, 27, 1),  # very light pink to dark red
        (44, 20, 1),  # pale flesh to brown
        (69, 26, 1),  # white to very dark grey
        (95, 14, 1),  # bright green to ~black
        (109, 12, 1), # light tan to dark tan
        (126, 4, 1),  # olive drab
        (130, 7, 1),  # light gold to gold brown
        (137, 18, 1), # white to dark red
        (155, 14, 1), # white to dark blue
        (169, 11, 1), # white to orange
        (180, 7, 1),  # white to yellow
        (187, 4, 1),  # orange to burnt orange
        (193, 7, 1),  # dark blue to black
        (201, 5, 1)   # light magenta to dark purple
    ],
    'quake': [
        (16, 15, -1),  # white to black
        (32, 16, -1),  # mustard to black
        (48, 16, -1),  # lavender to black
        (63, 15, -1),  # olive to black
        (79, 16, -1),  # red to black
        (92, 13, -1),  # orange to ~black
        (108, 16, -1), # yellow to orange to ~black
        (124, 16, -1), # pale flesh to ~black
        (125, 16, 1),  # light purple to ~black
        (141, 13, 1),  # purpleish pink to ~black
        (154, 15, 1),  # light tan to ~black
        (169, 16, 1),  # light olive to ~black
        (185, 14, 1),  # yellow to ~black
        (199, 31, 1),  # blue to black to light orange
        (233, 4, -1),  # yellow to brown
        (236, 3, -1),  # light blue to blue
        (240, 4, -1),  # red to dark red
        (243, 3, -1)   # white to yellow
    ],
    'heretic': [
        (35, 35, -1),  # white to black
        (51, 16, -1),  # light grey to dark grey
        (65, 14, -1),  # white to dark violent-grey
        (94, 29, -1),  # white to dark brown
        (110, 16, -1), # light tan to brown
        (136, 26, -1), # light yellow to dark golden brown
        (144, 8, -1),  # yellow to orange
        (160, 16, -1), # red to dark red
        (168, 8, -1),  # white to pink
        (176, 8, -1),  # light magenta to dark magenta
        (184, 8, -1),  # white to purple
        (208, 24, -1), # white to cyan to dark blue
        (224, 16, -1), # light green to dark green
        (240, 16, -1), # olive to dark olive
        (247, 7, -1)   # red to yellow
    ],
    'atari': [
        (113, 8, -16), # white to black
        (114, 8, -16), # yellow to muddy brown
        (115, 8, -16), # dull gold to brown
        (116, 8, -16), # peach to burnt orange
        (117, 8, -16), # pink to red
        (118, 8, -16), # magenta to dark magenta
        (119, 8, -16), # purple to dark purple
        (120, 8, -16), # violet to dark violet
        (121, 8, -16), # light blue to dark blue
        (122, 8, -16), # light cobalt to dark cobalt
        (123, 8, -16), # light teal to dark teal
        (124, 8, -16), # light sea green to dark sea green
        (125, 8, -16), # light green to dark green
        (126, 8, -16), # yellow green to dark yellow green
        (127, 8, -16), # pale yellow to dark olive
        (128, 8, -16)  # gold to golden brown
    ]
}


class RampIterator:
    
    def __init__(self, flower):
        ramp_def = random.choice(PALETTE_RAMPS[flower.art.palette.name])
        self.start, self.length, self.stride = ramp_def
        self.end = self.start + (self.length * self.stride)
        # determine starting color, somewhere along ramp
        self.start_step = random.randint(0, self.length - 1)
        self.color = self.start + (self.start_step * self.stride)
    
    def go_to_next_color(self):
        self.color += self.stride
        return self.color
