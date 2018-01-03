
# PETSCII Fireplace for Playscii
# https://jp.itch.io/petscii-fireplace

"""
High level approach here is to use a single GameObject that occupies the whole
screen, and draw to it using virtual (don't directly render) simulated particles.
This is more like a traditional 3D particle system, and fairly computationally
expensive compared to many old demoscene fire tricks. But it's easy to think about
and tune, which was the right call for a one-day exercise :]
"""

import webbrowser
from random import random, randint, choice

from game_object import GameObject
from art import TileIter

#
# some tuning knobs
#

# total # of particles to spawn and maintain;
# user can change this at runtime with +/-
TARGET_PARTICLES_DEFAULT = 100
# don't fill entire bottom of screen with fire; let it drift up and out
SPAWN_MARGIN_X = 8
# each particle's character "decays" towards 0 in random jumps
CHAR_DECAY_RATE_MAX = 16
# music is just an OGG file, modders feel free to provide your own
PLAY_MUSIC = False
MUSIC_FILENAME = 'music.ogg'
MUSIC_URL = 'http://brotherandroid.com'
# random ranges for time in seconds til next message pops up
MESSAGE_DELAY_MIN, MESSAGE_DELAY_MAX = 300, 600
MESSAGES = [
    'Happy Holidays',
    'Merry Christmas',
    'Happy New Year',
    'Happy Hanukkah',
    'Happy Kwanzaa',
    'Feliz Navidad',
    'Joyeux Noel'
]


class Fireplace(GameObject):
    
    "The main game object, manages particles, handles input, draws the fire."
    
    generate_art = True
    art_charset = 'c64_petscii'
    art_width, art_height = 54, 30 # approximately 16x9 aspect
    art_palette = 'fireplace'
    handle_key_events = True
    
    def pre_first_update(self):
        self.art.add_layer(z=0.01)
        self.target_particles = TARGET_PARTICLES_DEFAULT
        # get list of character indices, sorted based on # of non-blank pixels.
        # this correlates roughly with visual density, so each particle can
        # appear to fizzle out over time.
        chars = list(range(self.art.charset.last_index))
        weights = {}
        for i in chars:
            pixels = self.art.charset.get_solid_pixels_in_char(i)
            weights[i] = pixels
        self.weighted_chars = sorted(chars, key=weights.__getitem__)
        # spawn initial particles
        self.particles = []
        for i in range(self.target_particles):
            p = FireParticle(self)
            self.particles.append(p)
        # help screen
        self.help_screen = self.world.spawn_object_of_class("HelpScreen", 0, 0)
        self.help_screen.z = 1
        self.help_screen.set_scale(0.75, 0.75, 1)
        # start with help screen up, uncomment to hide on start
        #self.help_screen.visible = False
        # don't bother creating credit screen if !PLAY_MUSIC
        self.credit_screen = None
        if PLAY_MUSIC:
            self.world.play_music(MUSIC_FILENAME)
            self.music_paused = False
            # music credit screen, click for link to artist's website
            self.credit_screen = self.world.spawn_object_of_class("CreditScreen", 0, -6)
            self.credit_screen.z = 1.1
            self.credit_screen.set_scale(0.75, 0.75, 1)
        self.set_new_message_time()
    
    def update(self):
        # shift messages on layer 2 upward gradually
        if self.app.frames % 10 == 0:
            self.art.shift(0, 1, 0, -1)
        # at random intervals, print a friendly message on screen
        if self.world.get_elapsed_time() / 1000 > self.next_message_time:
            self.post_new_message()
            self.set_new_message_time()
        # update all particles, then mark for deletion in a separate list.
        # newbie tip: iterating through a list while removing items from it
        # can lead to bad bugs!
        for p in self.particles:
            p.update()
        to_destroy = []
        for p in self.particles:
            # cull particles that go out off screen
            if p.y < 0:
                to_destroy.append(p)
            if p.x < 0 or p.x > self.art.width - 1:
                to_destroy.append(p)
            # possible future optimization: {(x,y):[particles]} spatial dict?
            # for now just iterate through every pair
            for other in self.particles:
                if p is other:
                    continue
                if other in to_destroy:
                    continue
                # merge colors & chars if we overlap another, then destroy it
                if p.x == other.x and p.y == other.y:
                    p.merge(other)
                    to_destroy.append(other)
            # cull particles that have "gone out"
            if p.char <= 0:
                to_destroy.append(p)
            if p.fg <= 0 and p.bg <= 0:
                to_destroy.append(p)
        for p in to_destroy:
            if p in self.particles:
                # once removed from this list, particle will be garbage-collected
                self.particles.remove(p)
        # dim existing tiles
        for frame, layer, x, y in TileIter(self.art):
            # dim message layer at a lower rate
            if layer == 1 and self.app.frames % 3 != 0:
                continue
            if randint(0, 4) == 1:
                ch, fg, bg, _ = self.art.get_tile_at(frame, layer, x, y)
                # don't decay char index for messages on layer 2 to keep it legible
                if y != 0 and layer == 0:
                    ch = self.weighted_chars[ch - 1]
                self.art.set_tile_at(frame, layer, x, y, ch, fg - 1, bg - 1)
        # draw particles
        # (looks nicer if we don't clear between frames, actually)
        #self.art.clear_frame_layer(0, 0)
        for p in self.particles:
            self.art.set_tile_at(0, 0, p.x, p.y, self.weighted_chars[p.char], p.fg, p.bg)
        # spawn new particles to maintain target count
        while len(self.particles) < self.target_particles:
            p = FireParticle(self)
            self.particles.append(p)
        GameObject.update(self)
    
    def set_new_message_time(self):
        self.next_message_time = self.world.get_elapsed_time() / 1000 + randint(MESSAGE_DELAY_MIN, MESSAGE_DELAY_MAX)
    
    def post_new_message(self):
        msg_text = choice(MESSAGES)
        x = randint(0, self.art.width - len(msg_text))
        # spawn in lower half of screen
        y = randint(int(self.art.height / 2), self.art.height)
        # write to second layer
        self.art.write_string(0, 1, x, y, msg_text, randint(12, 16))
    
    def handle_key_down(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        # in many Playscii games all input goes through the Player object;
        # here input is handled by this object.
        if key == 'escape' and not self.world.app.can_edit:
            self.world.app.should_quit = True
        elif key == 'h':
            self.help_screen.visible = not self.help_screen.visible
            if self.credit_screen:
                self.credit_screen.visible = not self.credit_screen.visible
        elif key == 'm' and PLAY_MUSIC:
            if self.music_paused:
                self.world.resume_music()
                self.music_paused = False
            else:
                self.world.pause_music()
                self.music_paused = True
        elif key == 'c':
            if not self.app.fb.disable_crt:
                self.app.fb.toggle_crt()
        elif key == '=' or key == '+':
            self.target_particles += 10
            self.art.write_string(0, 0, 0, 0, 'Embers: %s' % self.target_particles, 15, 1)
        elif key == '-':
            if self.target_particles <= 10:
                return
            self.target_particles -= 10
            self.art.write_string(0, 0, 0, 0, 'Embers: %s' % self.target_particles, 15, 1)


class FireParticle:
    
    "Simulated particle, spawned and ticked and rendered by a Fireplace object."
    
    def __init__(self, fp):
        # pick char and color here; Fireplace should just run sim
        self.y = fp.art.height
        # spawn at random point along bottom edge, within margin
        self.x  = randint(SPAWN_MARGIN_X, fp.art.width - SPAWN_MARGIN_X)
        # char here is not character index but density, which decays;
        # fp.weighted_chars is used to look up actual index
        self.char = randint(100, fp.art.charset.last_index - 1)
        # spawn with random foreground + background colors
        # idea: spawn with relatively high brightness,
        # ie high density bright FG, low density bright BG?
        # (update: this didn't end up being necessary, more noisy is good)
        self.fg = randint(0, len(fp.art.palette.colors) - 1)
        self.bg = randint(0, len(fp.art.palette.colors) - 1)
        # hang on to fireplace
        self.fp = fp
    
    def update(self):
        # no need for out-of-range checks; fireplace will cull particles that
        # reach the top of the screen
        self.y -= randint(1, 2)
        # randomly move up, up-left, or up-right
        self.x += randint(-1, 1)
        # reduce char index by randomized rate
        self.char -= randint(1, CHAR_DECAY_RATE_MAX)
        # dim fg/bg colors by randomized rate
        self.fg -= randint(0, 1)
        self.bg -= randint(0, 1)
        # don't bother with range checks on colors;
        # if random embers "flare up" that's cool
        #self.fg = max(0, self.fg)
        #self.bg = max(0, self.bg)
    
    def merge(self, other):
        # merge (sum w/ other) colors & chars (ie when particles overlap)
        self.char += other.char
        self.fg += other.fg
        self.bg += other.bg


class HelpScreen(GameObject):
    art_src = 'help'
    alpha = 0.7


class CreditScreen(GameObject):
    
    "Separate object for the clickable area of the help screen."
    
    art_src = 'credit'
    alpha = 0.7
    handle_mouse_events = True
    
    def clicked(self, button, mouse_x, mouse_y):
        if self.visible:
            webbrowser.open(MUSIC_URL)
    
    def hovered(self, mouse_x, mouse_y):
        # hilight text on hover
        for frame, layer, x, y in TileIter(self.art):
            self.art.set_color_at(frame, layer, x, y, 2)
    
    def unhovered(self, mouse_x, mouse_y):
        for frame, layer, x, y in TileIter(self.art):
            self.art.set_color_at(frame, layer, x, y, 16)
