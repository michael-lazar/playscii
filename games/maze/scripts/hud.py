
from game_hud import GameHUD, GameHUDRenderable

class MazeHUD(GameHUD):

    message_color = 4
    
    def __init__(self, world):
        GameHUD.__init__(self, world)
        self.msg_art = self.world.app.new_art('mazehud_msg', 42, 1,
                                              'jpetscii', 'c64_original')
        self.msg = GameHUDRenderable(self.world.app, self.msg_art)
        self.arts = [self.msg_art]
        self.renderables = [self.msg]
        self.msg.x = -0.9
        self.msg.y = 0.9
        aspect = self.world.app.window_height / self.world.app.window_width
        self.msg.scale_x = 0.075 * aspect
        self.msg.scale_y = 0.05
        self.current_msg = ''
        self.msg_art.clear_frame_layer(0, 0, 0, self.message_color)
        self.post_msg('Welcome to MAZE, the amazing example game!')
    
    def post_msg(self, msg_text):
        self.current_msg = msg_text
        self.msg_art.clear_frame_layer(0, 0, 0, self.message_color)
        self.msg_art.write_string(0, 0, 0, 0, self.current_msg)
