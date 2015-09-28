
from ui_menu_pulldown_item import PulldownMenuItem, SeparatorItem, PulldownMenuData, FileQuitItem

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
# change current room... (show room list)
# show all rooms / hide all but current room
# add new room (new room dialog)
# delete current room (set current room to none, show all rooms)
# add/remove objects from room... (show object list)
# [X] list only objects in current room
class StubRoomItem(PulldownMenuItem):
    label = 'STUB'
    def should_dim(app): return True

#
# object menu
#
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

# TODO object menu:
# edit selected's room list... (go to room list)

class GameMenuData(PulldownMenuData):
    items = [HideEditUIItem, SeparatorItem, NewGameDirItem, SetGameDirItem,
             PauseGameItem, SeparatorItem, FileQuitItem]

class GameStateMenuData(PulldownMenuData):
    items = [ResetStateItem, LoadStateItem, SaveStateItem, SaveNewStateItem]

class GameWorldMenuData(PulldownMenuData):
    items = [EditWorldPropertiesItem]

class GameRoomMenuData(PulldownMenuData):
    items = [StubRoomItem]

class GameObjectMenuData(PulldownMenuData):
    items = [SpawnObjectItem, DuplicateObjectsItem, SeparatorItem,
             SelectObjectsItem, EditArtForObjectsItem]
