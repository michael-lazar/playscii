
from ui_dialog import UIDialog, Field

from ui_console import SetGameDirCommand, LoadGameStateCommand, SaveGameStateCommand
from ui_list_operations import LO_NONE, LO_SELECT_OBJECTS, LO_SET_SPAWN_CLASS, LO_LOAD_STATE, LO_SET_ROOM, LO_SET_ROOM_OBJECTS, LO_SET_OBJECT_ROOMS, LO_OPEN_GAME_DIR, LO_SET_ROOM_EDGE_WARP


class NewGameDirDialog(UIDialog):
    title = 'New game'
    field0_label = 'Name of new game folder:'
    field1_label = 'Name of new game:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False),
        Field(label=field1_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Create'
    game_mode_visible = True
    
    # TODO: only allow names that don't already exist
    
    def get_initial_field_text(self, field_number):
        # provide a reasonable non-blank name
        if field_number == 0:
            return 'newgame'
        elif field_number == 1:
            return type(self.ui.app.gw).game_title
    
    def confirm_pressed(self):
        if self.ui.app.gw.create_new_game(self.field_texts[0], self.field_texts[1]):
            self.ui.app.enter_game_mode()
        self.dismiss()

class LoadGameStateDialog(UIDialog):
    
    title = 'Open game state'
    field_label = 'Game state file to open:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Open'
    game_mode_visible = True
    
    # TODO: only allow valid game state file in current game directory
    
    def confirm_pressed(self):
        LoadGameStateCommand.execute(self.ui.console, [self.field_texts[0]])
        self.dismiss()

class SaveGameStateDialog(UIDialog):
    
    title = 'Save game state'
    field_label = 'New filename for game state:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Save'
    game_mode_visible = True
    
    def confirm_pressed(self):
        SaveGameStateCommand.execute(self.ui.console, [self.field_texts[0]])
        self.dismiss()

class AddRoomDialog(UIDialog):
    title = 'Add new room'
    field0_label = 'Name for new room:'
    field1_label = 'Class of new room:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False),
        Field(label=field1_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Add'
    game_mode_visible = True
    invalid_room_name_error = 'Invalid room name.'
    
    def get_initial_field_text(self, field_number):
        # provide a reasonable non-blank name
        if field_number == 0:
            return 'Room ' + str(len(self.ui.app.gw.rooms) + 1)
        elif field_number == 1:
            return 'GameRoom'
    
    def is_input_valid(self):
        return self.field_texts[0] != '', self.invalid_room_name_error
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        self.ui.app.gw.add_room(self.field_texts[0], self.field_texts[1])
        self.dismiss()

class SetRoomCamDialog(UIDialog):
    title = 'Set room camera marker'
    tile_width = 48
    field0_label = 'Name of location marker object for this room:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Set'
    game_mode_visible = True
    
    def dismiss(self):
        self.ui.edit_list_panel.set_list_operation(LO_NONE)
        UIDialog.dismiss(self)
    
    def confirm_pressed(self):
        self.ui.app.gw.current_room.set_camera_marker_name(self.field_texts[0])
        self.dismiss()

class SetRoomEdgeWarpsDialog(UIDialog):
    title = 'Set room edge warps'
    tile_width = 48
    fields = 4
    field0_label = 'Name of room/object to warp at LEFT edge:'
    field1_label = 'Name of room/object to warp at RIGHT edge:'
    field2_label = 'Name of room/object to warp at TOP edge:'
    field3_label = 'Name of room/object to warp at BOTTOM edge:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False),
        Field(label=field1_label, type=str, width=field_width, oneline=False),
        Field(label=field2_label, type=str, width=field_width, oneline=False),
        Field(label=field3_label, type=str, width=field_width, oneline=False)
    ]
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
        room.left_edge_warp_dest_name = self.field_texts[0]
        room.right_edge_warp_dest_name = self.field_texts[1]
        room.top_edge_warp_dest_name = self.field_texts[2]
        room.bottom_edge_warp_dest_name = self.field_texts[3]
        room.reset_edge_warps()
        self.dismiss()

class SetRoomBoundsObjDialog(UIDialog):
    title = 'Set room edge object'
    field0_label = 'Name of object to use for room bounds:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False)
    ]
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
        room.warp_edge_bounds_obj_name = self.field_texts[0]
        room.reset_edge_warps()
        self.dismiss()

class RenameRoomDialog(UIDialog):
    title = 'Rename room'
    field0_label = 'New name for current room:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Rename'
    game_mode_visible = True
    invalid_room_name_error = 'Invalid room name.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return self.ui.app.gw.current_room.name
    
    def is_input_valid(self):
        return self.field_texts[0] != '', self.invalid_room_name_error
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        world = self.ui.app.gw
        world.rename_room(world.current_room, self.field_texts[0])
        self.dismiss()
