
from ui_dialog import UIDialog

from ui_console import SetGameDirCommand, LoadGameStateCommand, SaveGameStateCommand
from ui_list_operations import LO_NONE, LO_SELECT_OBJECTS, LO_SET_SPAWN_CLASS, LO_LOAD_STATE, LO_SET_ROOM, LO_SET_ROOM_OBJECTS, LO_SET_OBJECT_ROOMS, LO_OPEN_GAME_DIR, LO_SET_ROOM_EDGE_WARP


class NewGameDirDialog(UIDialog):
    title = 'New game'
    fields = 1
    field0_label = 'Name of new game directory:'
    confirm_caption = 'Create'
    game_mode_visible = True
    
    # TODO: only allow names that don't already exist
    
    def confirm_pressed(self):
        if self.ui.app.gw.create_new_game(self.field0_text):
            self.ui.app.enter_game_mode()
        self.dismiss()

class SetGameDirDialog(UIDialog):
    
    title = 'Open game'
    fields = 1
    field0_label = 'Directory to load game data from:'
    confirm_caption = 'Open'
    game_mode_visible = True
    
    # TODO: only allow valid game directory
    
    def confirm_pressed(self):
        SetGameDirCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()

class LoadGameStateDialog(UIDialog):
    
    title = 'Open game state'
    fields = 1
    field0_label = 'Game state file to open:'
    confirm_caption = 'Open'
    game_mode_visible = True
    
    # TODO: only allow valid game state file in current game directory
    
    def confirm_pressed(self):
        LoadGameStateCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()

class SaveGameStateDialog(UIDialog):
    
    title = 'Save game state'
    fields = 1
    field0_label = 'New filename for game state:'
    confirm_caption = 'Save'
    game_mode_visible = True
    
    def confirm_pressed(self):
        SaveGameStateCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()

class AddRoomDialog(UIDialog):
    title = 'Add new room'
    fields = 2
    field0_label = 'Name for new room:'
    field1_label = 'Class of new room:'
    confirm_caption = 'Add'
    game_mode_visible = True
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return ''
        elif field_number == 1:
            return 'GameRoom'
    
    def confirm_pressed(self):
        self.ui.app.gw.add_room(self.field0_text, self.field1_text)
        self.dismiss()

class SetRoomCamDialog(UIDialog):
    title = 'Set room camera marker'
    fields = 1
    field0_label = 'Name of location marker object for this room:'
    confirm_caption = 'Set'
    game_mode_visible = True
    
    def confirm_pressed(self):
        self.ui.app.gw.current_room.set_camera_marker_name(self.field0_text)
        self.dismiss()

class SetRoomEdgeWarpsDialog(UIDialog):
    title = 'Set room edge warps'
    tile_width = 48
    fields = 4
    field0_label = 'Name of room/object to warp at LEFT edge:'
    field1_label = 'Name of room/object to warp at RIGHT edge:'
    field2_label = 'Name of room/object to warp at TOP edge:'
    field3_label = 'Name of room/object to warp at BOTTOM edge:'
    field0_type = field1_type = field2_type = field3_type = str
    confirm_caption = 'Set'
    game_mode_visible = True
    
    def get_initial_field_text(self, field_number):
        room = self.ui.app.gw.current_room
        names = {0: room.left_edge_warp_dest_name, 1: room.right_edge_warp_dest_name,
                 2: room.top_edge_warp_dest_name, 3: room.bottom_edge_warp_dest_name}
        return names[field_number]
    
    def dismiss(self):
        self.ui.edit_list_panel.set_list_operation(LO_NONE)
        UIDialog.dismiss(self)
    
    def confirm_pressed(self):
        room = self.ui.app.gw.current_room
        room.left_edge_warp_dest_name = self.field0_text
        room.right_edge_warp_dest_name = self.field1_text
        room.top_edge_warp_dest_name = self.field2_text
        room.bottom_edge_warp_dest_name = self.field3_text
        room.reset_edge_warps()
        self.dismiss()

class SetRoomBoundsObjDialog(UIDialog):
    title = 'Set room edge object'
    fields = 1
    field0_label = 'Name of object to use for room bounds:'
    confirm_caption = 'Set'
    game_mode_visible = True
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return self.ui.app.gw.current_room.warp_edge_bounds_obj_name
    
    def dismiss(self):
        self.ui.edit_list_panel.set_list_operation(LO_NONE)
        UIDialog.dismiss(self)
    
    def confirm_pressed(self):
        room = self.ui.app.gw.current_room
        room.warp_edge_bounds_obj_name = self.field0_text
        room.reset_edge_warps()
        self.dismiss()

class RenameRoomDialog(UIDialog):
    title = 'Rename room'
    fields = 1
    field0_label = 'New name for current room:'
    confirm_caption = 'Rename'
    game_mode_visible = True
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return self.ui.app.gw.current_room.name
    
    def confirm_pressed(self):
        world = self.ui.app.gw
        world.rename_room(world.current_room, self.field0_text)
        self.dismiss()
