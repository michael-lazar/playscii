
from game_room import GameRoom


class MazeRoom(GameRoom):
    
    def exited(self, new_room):
        GameRoom.exited(self, new_room)
        # clear message line when exiting
        if self.world.hud:
            self.world.hud.post_msg('')


class OutsideRoom(MazeRoom):
    
    camera_follow_player = True
    
    def entered(self, old_room):
        MazeRoom.entered(self, old_room)
        self.world.collision_enabled = False
        self.world.app.camera.y_tilt = 4
    
    def exited(self, new_room):
        MazeRoom.exited(self, new_room)
        self.world.collision_enabled = True
        self.world.app.camera.y_tilt = 0
