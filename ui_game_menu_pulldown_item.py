
from ui_menu_pulldown_item import PulldownMenuItem, SeparatorItem, PulldownMenuData, FileQuitItem, ViewToggleCRTItem, ViewToggleCameraTiltItem

#
# game menu
#
class HideEditUIItem(PulldownMenuItem):
    label = 'Hide edit UI'
    command = 'toggle_game_edit_ui'
    close_on_select = True
    always_active = True

class NewGameDirItem(PulldownMenuItem):
    label = 'New game…'
    command = 'new_game_dir'
    always_active = True

class SetGameDirItem(PulldownMenuItem):
    label = 'Open game…'
    command = 'set_game_dir'
    close_on_select = True
    always_active = True

class PauseGameItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_anim_playback'
    always_active = True
    def get_label(app):
        return ['Pause game', 'Unpause game'][app.gw.paused]

#
# state menu
#
class ResetStateItem(PulldownMenuItem):
    label = 'Reset to last state'
    command = 'reset_game'
    close_on_select = True
    always_active = True

class LoadStateItem(PulldownMenuItem):
    label = 'Load state…'
    command = 'load_game_state'
    close_on_select = True
    always_active = True

class SaveStateItem(PulldownMenuItem):
    label = 'Save current state'
    command = 'save_current'
    close_on_select = True
    always_active = True

class SaveNewStateItem(PulldownMenuItem):
    label = 'Save new state…'
    command = 'save_game_state'
    always_active = True

#
# view menu
#
class ObjectsToCameraItem(PulldownMenuItem):
    label = 'Move selected object(s) to camera'
    command = 'objects_to_camera'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0

class CameraToObjectsItem(PulldownMenuItem):
    label = 'Move camera to selected object'
    command = 'camera_to_objects'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) != 1

#
# world menu
#
class EditWorldPropertiesItem(PulldownMenuItem):
    label = 'Edit world properties…'
    command = 'edit_world_properties'
    close_on_select = True
    always_active = True

#
# room menu
#

# TODO room menu:
# [X] list only objects in current room
# rename room

class ChangeRoomItem(PulldownMenuItem):
    label = 'Change current room…'
    command = 'change_current_room'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.rooms) == 0

class AddRoomItem(PulldownMenuItem):
    label = 'Add room…'
    command = 'add_room'
    always_active = True

class SetRoomObjectsItem(PulldownMenuItem):
    label = 'Add/remove objects from room…'
    command = 'set_room_objects'
    close_on_select = True
    def should_dim(app):
        return app.gw.current_room is None

class RemoveRoomItem(PulldownMenuItem):
    label = 'Remove this room'
    command = 'remove_current_room'
    close_on_select = True
    def should_dim(app):
        return app.gw.current_room is None

class ToogleAllRoomsVizItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_all_rooms_visible'
    def should_dim(app):
        return len(app.gw.rooms) == 0
    def get_label(app):
        return ['Show all rooms', 'Show only current room'][app.gw.show_all_rooms]

class SetRoomCameraItem(PulldownMenuItem):
    label = "Set this room's camera marker…"
    command = 'set_room_camera_marker'
    def should_dim(app):
        return app.gw.current_room is None

class SetRoomEdgeDestinationsItem(PulldownMenuItem):
    label = "Set this room's edge warps…"
    command = 'set_room_edge_warps'
    def should_dim(app):
        return app.gw.current_room is None

class SetRoomBoundsObject(PulldownMenuItem):
    label = "Set this room's edge object…"
    command = 'set_room_bounds_obj'
    def should_dim(app):
        return app.gw.current_room is None

class AddSelectedToCurrentRoomItem(PulldownMenuItem):
    label = 'Add selected objects to this room'
    command = 'add_selected_to_room'
    def should_dim(app):
        return app.gw.current_room is None or len(app.gw.selected_objects) == 0

class RemoveSelectedFromCurrentRoomItem(PulldownMenuItem):
    label = 'Remove selected objects from this room'
    command = 'remove_selected_from_room'
    def should_dim(app):
        return app.gw.current_room is None or len(app.gw.selected_objects) == 0

#
# object menu
#

# TODO object menu:
# edit selected's room list... (go to room list)

class SpawnObjectItem(PulldownMenuItem):
    label = 'Spawn object…'
    command = 'choose_spawn_object_class'
    close_on_select = True
    always_active = True

class DuplicateObjectsItem(PulldownMenuItem):
    label = 'Duplicate selected objects'
    command = 'duplicate_selected_objects'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0

class SelectObjectsItem(PulldownMenuItem):
    label = 'Select objects…'
    command = 'select_objects'
    close_on_select = True
    always_active = True

class EditArtForObjectsItem(PulldownMenuItem):
    label = 'Edit art for selected…'
    command = 'edit_art_for_selected_objects'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0


class GameMenuData(PulldownMenuData):
    items = [HideEditUIItem, SeparatorItem, NewGameDirItem, SetGameDirItem,
             PauseGameItem, SeparatorItem, FileQuitItem]

class GameStateMenuData(PulldownMenuData):
    items = [ResetStateItem, LoadStateItem, SaveStateItem, SaveNewStateItem]

class GameViewMenuData(PulldownMenuData):
    items = [ViewToggleCRTItem, ViewToggleCameraTiltItem, SeparatorItem,
             ObjectsToCameraItem, CameraToObjectsItem]
    
    def should_mark_item(item, ui):
        if hasattr(item, 'should_mark'):
            return item.should_mark(ui)
        return False

class GameWorldMenuData(PulldownMenuData):
    items = [EditWorldPropertiesItem]

class GameRoomMenuData(PulldownMenuData):
    items = [ChangeRoomItem, AddRoomItem, RemoveRoomItem, ToogleAllRoomsVizItem,
             SeparatorItem, SetRoomObjectsItem, RemoveSelectedFromCurrentRoomItem,
             AddSelectedToCurrentRoomItem, SeparatorItem, SetRoomCameraItem, 
             SetRoomEdgeDestinationsItem, SetRoomBoundsObject,
             SeparatorItem
    ]
    def should_mark_item(item, ui):
        "show checkmark for current room"
        if not ui.app.gw.current_room:
            return False
        return ui.app.gw.current_room.name == item.cb_arg
    
    def get_items(app):
        items = []
        if len(app.gw.rooms) == 0:
            return items
        # TODO: this is almost c+p'd from LayerMenuData, generalize it
        # first determine longest line to set width of items
        longest_line = 0
        for room_name in app.gw.rooms:
            if len(room_name) > longest_line:
                longest_line = len(room_name)
        # check non-generated menu items too
        for item in GameRoomMenuData.items:
            if len(item.label) + 1 > longest_line:
                longest_line = len(item.label) + 1
        # cap at max allowed line length
        for room_name,room in app.gw.rooms.items():
            class TempMenuItemClass(PulldownMenuItem): pass
            item = TempMenuItemClass
            # leave spaces for mark
            item.label = '  %s' % room_name
            # pad, put Z depth on far right
            item.label = item.label.ljust(longest_line)
            # trim to keep below a max length
            item.label = item.label[:longest_line]
            # tell PulldownMenu's button creation process not to auto-pad
            item.no_pad = True
            item.command = 'change_current_room_to'
            item.cb_arg = room_name
            items.append(item)
        return items


class GameObjectMenuData(PulldownMenuData):
    items = [SpawnObjectItem, DuplicateObjectsItem, SeparatorItem,
             SelectObjectsItem, EditArtForObjectsItem]
