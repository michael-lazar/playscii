
from game_hud import GameHUD, GameHUDRenderable

class MazeHUD(GameHUD):
    
    def __init__(self, world):
        GameHUD.__init__(self, world)
        self.msg_art = self.world.app.new_art('mazehud_msg', 20, 1,
                                              'jpetscii', 'c64_original')
        self.msg = GameHUDRenderable(self.world.app, self.msg_art)
        self.arts = [self.msg_art]
        self.renderables = [self.msg]
        self.msg.x = -0.9
        self.msg.y = 0.9
        self.msg.scale_x = 0.1
        self.msg.scale_y = 0.1
        self.current_msg = ''
        self.post_msg('hellooo')
    
    def post_msg(self, msg_text):
        self.current_msg = msg_text
        self.msg_art.clear_frame_layer(0, 0, 0, 4)
        self.msg_art.write_string(0, 0, 0, 0, self.current_msg)
