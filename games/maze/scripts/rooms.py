
from game_room import GameRoom

class OutsideRoom(GameRoom):
    
    camera_follow_player = True
    
    def entered(self, old_room):
        GameRoom.entered(self, old_room)
        self.world.collision_enabled = False
        self.world.app.camera.y_tilt = 4
    
    def exited(self, new_room):
        GameRoom.exited(self, new_room)
        self.world.collision_enabled = True
        self.world.app.camera.y_tilt = 0
