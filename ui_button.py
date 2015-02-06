
from ui_colors import UIColors

TEXT_LEFT = 0
TEXT_CENTER = 1
TEXT_RIGHT = 2

BUTTON_STATES = ['normal', 'hovered', 'clicked', 'dimmed']

class UIButton:
    
    "clickable button that does something in a UIElement"
    
    # x/y/width/height given in tile scale
    x, y = 0, 0
    width, height = 1, 1
    caption = 'TEST'
    caption_justify = TEXT_LEFT
    # paint caption from string, or not
    should_draw_caption = True
    caption_y = 0
    callback = None
    normal_fg_color = UIColors.black
    normal_bg_color = UIColors.lightgrey
    hovered_fg_color = UIColors.black
    hovered_bg_color = UIColors.white
    clicked_fg_color = UIColors.white
    clicked_bg_color = UIColors.black
    dimmed_fg_color = UIColors.black
    dimmed_bg_color = UIColors.medgrey
    # dimmed is a special, alternative-to-normal state
    dimmed = False
    can_hover = True
    can_click = True
    visible = True
    
    def __init__(self, element, starting_state=None):
        self.element = element
        self.state = starting_state or 'normal'
    
    def log_event(self, event_type):
        "common code for button event logging"
        if self.element.ui.logg:
            self.element.ui.app.log("UIButton: %s's %s %s" % (self.element.__class__.__name__, self.__class__.__name__, event_type))
    
    def set_state(self, new_state):
        if not new_state in BUTTON_STATES:
            self.element.ui.app.log('Unrecognized state for button %s: %s' % (self.__class__.__name__, new_state))
            return
        self.state = new_state
        self.set_state_colors()
    
    def get_state_colors(self, state):
        fg = getattr(self, '%s_fg_color' % state)
        bg = getattr(self, '%s_bg_color' % state)
        return fg, bg
    
    def set_state_colors(self):
        # set colors for entire button area based on current state
        if self.dimmed and self.state == 'normal':
            self.state = 'dimmed'
        fg, bg = self.get_state_colors(self.state)
        for y in range(self.height):
            for x in range(self.width):
                self.element.art.set_tile_at(0, 0, self.x + x, self.y + y, None, fg, bg)
    
    def hover(self):
        self.log_event('hovered')
        self.set_state('hovered')
    
    def unhover(self):
        self.log_event('unhovered')
        if self.dimmed:
            self.set_state('dimmed')
        else:
            self.set_state('normal')
    
    def click(self):
        self.log_event('clicked')
        self.set_state('clicked')
    
    def unclick(self):
        self.log_event('unclicked')
        if self in self.element.hovered_buttons:
            self.hover()
        else:
            self.unhover()
    
    def draw_caption(self):
        y = self.y + self.caption_y
        text = self.caption
        if self.caption_justify == TEXT_CENTER:
            text = text.center(self.width)
        elif self.caption_justify == TEXT_RIGHT:
            text = text.rjust(self.width)
        # leave FG color None; should already have been set
        self.element.art.write_string(0, 0, self.x, y, text, None)
    
    def draw(self):
        self.set_state_colors()
        if self.should_draw_caption and self.caption != '':
            self.draw_caption()