# coding=utf-8

from ui_menu_pulldown_item import PulldownMenuItem, SeparatorItem, PulldownMenuData, FileQuitItem, ViewToggleCRTItem, ViewToggleCameraTiltItem, ViewSetZoomItem, ViewToggleGridItem

class GameModePulldownMenuItem(PulldownMenuItem):
    # unless overridden, game mode items not allowed in art mode
    art_mode_allowed = False


#
# game menu
#
class HideEditUIItem(GameModePulldownMenuItem):
    label = 'Hide edit UI'
    command = 'toggle_game_edit_ui'
    close_on_select = True
    always_active = True

class NewGameDirItem(GameModePulldownMenuItem):
    label = 'New game…'
    command = 'new_game_dir'
    always_active = True

class SetGameDirItem(GameModePulldownMenuItem):
    label = 'Open game…'
    command = 'set_game_dir'
    close_on_select = True
    always_active = True

class PauseGameItem(GameModePulldownMenuItem):
    label = 'blah'
    command = 'toggle_anim_playback'
    always_active = True
    def get_label(app):
        return ['Pause game', 'Unpause game'][app.gw.paused]

class OpenConsoleItem(GameModePulldownMenuItem):
    label = 'Open dev console'
    command = 'toggle_console'
    close_on_select = True
    always_active = True
    art_mode_allowed = True

#
# state menu
#
class ResetStateItem(GameModePulldownMenuItem):
    label = 'Reset to last state'
    command = 'reset_game'
    close_on_select = True
    def should_dim(app):
        return not app.gw.game_dir

class LoadStateItem(GameModePulldownMenuItem):
    label = 'Load state…'
    command = 'load_game_state'
    close_on_select = True
    def should_dim(app):
        return not app.gw.game_dir

class SaveStateItem(GameModePulldownMenuItem):
    label = 'Save current state'
    command = 'save_current'
    close_on_select = True
    def should_dim(app):
        return not app.gw.game_dir

class SaveNewStateItem(GameModePulldownMenuItem):
    label = 'Save new state…'
    command = 'save_game_state'
    def should_dim(app):
        return not app.gw.game_dir

#
# view menu
#
class ObjectsToCameraItem(GameModePulldownMenuItem):
    label = 'Move selected object(s) to camera'
    command = 'objects_to_camera'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0

class CameraToObjectsItem(GameModePulldownMenuItem):
    label = 'Move camera to selected object'
    command = 'camera_to_objects'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) != 1

class ToggleDebugObjectsItem(GameModePulldownMenuItem):
    label = '  Draw debug objects'
    command = 'toggle_debug_objects'
    def should_dim(app):
        return not app.gw.game_dir
    def should_mark(ui):
        return ui.app.gw.properties and ui.app.gw.properties.draw_debug_objects

class ToggleOriginVizItem(GameModePulldownMenuItem):
    label = '  Show all object origins'
    command = 'toggle_all_origin_viz'
    def should_dim(app):
        return not app.gw.game_dir
    def should_mark(ui):
        return ui.app.gw.show_origin_all

class ToggleBoundsVizItem(GameModePulldownMenuItem):
    label = '  Show all object bounds'
    command = 'toggle_all_bounds_viz'
    def should_dim(app):
        return not app.gw.game_dir
    def should_mark(ui):
        return ui.app.gw.show_bounds_all

class ToggleCollisionVizItem(GameModePulldownMenuItem):
    label = '  Show all object collision'
    command = 'toggle_all_collision_viz'
    def should_dim(app):
        return not app.gw.game_dir
    def should_mark(ui):
        return ui.app.gw.show_collision_all

#
# world menu
#
class EditWorldPropertiesItem(GameModePulldownMenuItem):
    label = 'Edit world properties…'
    command = 'edit_world_properties'
    close_on_select = True
    def should_dim(app):
        return not app.gw.game_dir

#
# room menu
#

class ChangeRoomItem(GameModePulldownMenuItem):
    label = 'Change current room…'
    command = 'change_current_room'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.rooms) == 0

class AddRoomItem(GameModePulldownMenuItem):
    label = 'Add room…'
    command = 'add_room'
    def should_dim(app):
        return not app.gw.game_dir

class SetRoomObjectsItem(GameModePulldownMenuItem):
    label = 'Add/remove objects from room…'
    command = 'set_room_objects'
    close_on_select = True
    def should_dim(app):
        return app.gw.current_room is None

class RemoveRoomItem(GameModePulldownMenuItem):
    label = 'Remove this room'
    command = 'remove_current_room'
    close_on_select = True
    def should_dim(app):
        return app.gw.current_room is None

class RenameRoomItem(GameModePulldownMenuItem):
    label = 'Rename this room…'
    command = 'rename_current_room'
    def should_dim(app):
        return app.gw.current_room is None

class ToggleAllRoomsVizItem(GameModePulldownMenuItem):
    label = 'blah'
    command = 'toggle_all_rooms_visible'
    def should_dim(app):
        return len(app.gw.rooms) == 0
    def get_label(app):
        return ['Show all rooms', 'Show only current room'][app.gw.show_all_rooms]

class ToggleListOnlyRoomObjectItem(GameModePulldownMenuItem):
    label = '  List only objects in this room'
    command = 'toggle_list_only_room_objects'
    def should_dim(app):
        return len(app.gw.rooms) == 0
    def should_mark(ui):
        return ui.app.gw.list_only_current_room_objects

class ToggleRoomCamerasItem(GameModePulldownMenuItem):
    label = '  Camera changes with room'
    command = 'toggle_room_camera_changes'
    def should_dim(app):
        return len(app.gw.rooms) == 0
    def should_mark(ui):
        return ui.app.gw.room_camera_changes_enabled

class SetRoomCameraItem(GameModePulldownMenuItem):
    label = "Set this room's camera marker…"
    command = 'set_room_camera_marker'
    def should_dim(app):
        return app.gw.current_room is None

class SetRoomEdgeDestinationsItem(GameModePulldownMenuItem):
    label = "Set this room's edge warps…"
    command = 'set_room_edge_warps'
    def should_dim(app):
        return app.gw.current_room is None

class SetRoomBoundsObject(GameModePulldownMenuItem):
    label = "Set this room's edge object…"
    command = 'set_room_bounds_obj'
    def should_dim(app):
        return app.gw.current_room is None

class AddSelectedToCurrentRoomItem(GameModePulldownMenuItem):
    label = 'Add selected objects to this room'
    command = 'add_selected_to_room'
    def should_dim(app):
        return app.gw.current_room is None or len(app.gw.selected_objects) == 0

class RemoveSelectedFromCurrentRoomItem(GameModePulldownMenuItem):
    label = 'Remove selected objects from this room'
    command = 'remove_selected_from_room'
    def should_dim(app):
        return app.gw.current_room is None or len(app.gw.selected_objects) == 0

#
# object menu
#

class SpawnObjectItem(GameModePulldownMenuItem):
    label = 'Spawn object…'
    command = 'choose_spawn_object_class'
    close_on_select = True
    def should_dim(app):
        return not app.gw.game_dir

class DuplicateObjectsItem(GameModePulldownMenuItem):
    label = 'Duplicate selected objects'
    command = 'duplicate_selected_objects'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0

class SelectObjectsItem(GameModePulldownMenuItem):
    label = 'Select objects…'
    command = 'select_objects'
    close_on_select = True
    def should_dim(app):
        return not app.gw.game_dir

class EditArtForObjectsItem(GameModePulldownMenuItem):
    label = 'Edit art for selected…'
    command = 'edit_art_for_selected_objects'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0

class SetObjectRoomsItem(GameModePulldownMenuItem):
    label = 'Add/remove this object from rooms…'
    command = 'set_object_rooms'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) != 1

class DeleteSelectedObjectsItem(GameModePulldownMenuItem):
    label = 'Delete selected object(s)'
    command = 'erase_selection_or_art'
    close_on_select = True
    def should_dim(app):
        return len(app.gw.selected_objects) == 0

class GameMenuData(PulldownMenuData):
    items = [HideEditUIItem, OpenConsoleItem, SeparatorItem,
             NewGameDirItem, SetGameDirItem, PauseGameItem, SeparatorItem,
             FileQuitItem]

class GameStateMenuData(PulldownMenuData):
    items = [ResetStateItem, LoadStateItem, SaveStateItem, SaveNewStateItem]

class GameViewMenuData(PulldownMenuData):
    items = [ViewToggleCRTItem, ViewToggleGridItem, SeparatorItem,
             ViewSetZoomItem, ViewToggleCameraTiltItem, SeparatorItem,
             ObjectsToCameraItem, CameraToObjectsItem, ToggleDebugObjectsItem,
             ToggleOriginVizItem, ToggleBoundsVizItem, ToggleCollisionVizItem]
    
    def should_mark_item(item, ui):
        if hasattr(item, 'should_mark'):
            return item.should_mark(ui)
        return False

class GameWorldMenuData(PulldownMenuData):
    items = [EditWorldPropertiesItem]

class GameRoomMenuData(PulldownMenuData):
    items = [ChangeRoomItem, AddRoomItem, RemoveRoomItem, RenameRoomItem,
             ToggleAllRoomsVizItem, ToggleListOnlyRoomObjectItem, ToggleRoomCamerasItem, SeparatorItem,
             AddSelectedToCurrentRoomItem, RemoveSelectedFromCurrentRoomItem,
             SetRoomObjectsItem, SeparatorItem,
             SetRoomCameraItem, SetRoomEdgeDestinationsItem, SetRoomBoundsObject,
             SeparatorItem
    ]
    def should_mark_item(item, ui):
        "show checkmark for current room"
        if not ui.app.gw.current_room:
            return False
        if hasattr(item, 'should_mark'):
            return item.should_mark(ui)
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
            class TempMenuItemClass(GameModePulldownMenuItem): pass
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
        # sort room list alphabetically so it's stable, if arbitrary
        items.sort(key=lambda item: item.label, reverse=False)
        return items


class GameObjectMenuData(PulldownMenuData):
    items = [SpawnObjectItem, DuplicateObjectsItem, SeparatorItem,
             SelectObjectsItem, EditArtForObjectsItem, SetObjectRoomsItem,
             DeleteSelectedObjectsItem]
