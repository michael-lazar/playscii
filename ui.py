
UI_ASSET_DIR = 'ui/'

class UI:
    
    charset = 'ui'
    palette = 'c64'
    # low-contrast background texture that distinguishes UI from flat color
    bg_texture = 'bgnoise_alpha.png'
    
    def __init__(self, app, shader_lord, window_width, window_height):
        pass
    
    def window_resized(self, new_width, new_height):
        pass
    
    def update(self):
        pass
    
    def destroy(self):
        pass
    
    def render(self, elapsed_time):
        pass
