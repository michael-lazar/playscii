import sdl2

from ui_element import UIElement
from ui_dialog import UIDialog

class PagedInfoDialog(UIDialog):
    
    "dialog that presents multiple pages of info w/ buttons to navigate next/last page"
    
    title = 'Info'
    # message = list of page strings, each can be triple-quoted / contain line breaks
    message = ['']
    tile_width = 50
    fields = 0
    confirm_caption = '>>'
    other_caption = '<<'
    cancel_caption = 'Done'
    other_button_visible = True
    
    def __init__(self, ui):
        self.page = 0
        UIDialog.__init__(self, ui)
        self.reset_art()
    
    def update(self):
        # disable prev/next buttons if we're at either end of the page list
        if self.page == 0:
            self.other_button.can_hover = False
            self.other_button.set_state('dimmed')
        elif self.page == len(self.message) - 1:
            self.confirm_button.can_hover = False
            self.confirm_button.set_state('dimmed')
        else:
            for button in [self.confirm_button, self.other_button]:
                button.can_hover = True
                button.dimmed = False
                if button.state != 'normal':
                    button.set_state('normal')
        UIElement.update(self)
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        if keystr == 'Left':
            self.other_pressed()
        elif keystr == 'Right':
            self.confirm_pressed()
        elif keystr == 'Escape':
            self.cancel_pressed()
    
    def get_message(self):
        return self.message[self.page].rstrip().split('\n')
    
    def confirm_pressed(self):
        # confirm repurposed to "next page"
        if self.page < len(self.message) - 1:
            self.page += 1
            # redraw, tell reset_art not to resize
            self.reset_art(False)
    
    def cancel_pressed(self):
        self.dismiss()
    
    def other_pressed(self):
        # other repurposed to "previous page"
        if self.page > 0:
            self.page -= 1
            self.reset_art(False)


# TODO: full credits + patron thanks
about_message = [
"""
          by JP LeBreton (c) 2014-2015          |

Playscii was made with the support of many
nice people.

                     Patrons:

Katelyn Gigante, Andrew Yoder, Josh Closs,
Jacques Frechet, Nick Keirle, Rohit Nirmal,
Aubrey Hesselgren, Andrew Anderson,
Lachlan Cooper, Isaac Halvorson, Sam Crisp,
James Noble, Holger Dors, Chris Welch,
Aaron Brown, Leon Hartwig, Shannon Smith
""",
"""
      Programming Help and Contributions:

Shawn Walker, Sean Barrett, Mark Wonnacott,
Ian MacLarty, Goldbuick, Rohit Nirmal,
Tin Tvrtkovic, Sean Gubelman

            Tool Design Inspiration:

Anna Anthropy, Andi McClure, Bret Victor,
Tim Sweeney (ZZT), Craig Hickman (Kid Pix),
Bill Atkinson (HyperCard)
""",
"""
      Love, Encouragement, Moral Support:

L Stiger
Gail, Gil, and Elise LeBreton
Brendan Sinclair
Liz Ryerson
Johnnemann Nordhagen
Aubrey Hesselgren
Zak McClendon
#tool-design
"""
]

class AboutDialog(PagedInfoDialog):
    title = 'Playscii'
    message = about_message
    def __init__(self, ui):
        self.title += ' %s' % ui.app.version
        PagedInfoDialog.__init__(self, ui)


# TODO: proper help content
help_message = [
"""
Help is on the way!
:/
"""
]

class HelpScreenDialog(AboutDialog):
    message = help_message
