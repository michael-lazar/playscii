
from ui_menu_pulldown_item import PulldownMenuItem, PulldownMenuData, ToggleGameModeMenuItem

class FileNewMenuItem(PulldownMenuItem):
    label = 'New…'
    command = 'new_art'
    def should_dim(app):
        return False

class HideEditUIMenuItem(PulldownMenuItem):
    label = 'Hide edit UI'
    command = 'toggle_game_edit_ui'
    def should_dim(app):
        return False

class SelectObjectsMenuItem(PulldownMenuItem):
    label = 'Select objects…'
    command = 'select_objects'
    def should_dim(app):
        return False

# TODO game menu:
# reset game
# pause/unpause game
# open game dir...
# new game...
# load state...
# save current state
# save state as...
# edit world properties...

# TODO room menu:
# change current room... (show room list)
# show all rooms / hide all but current room
# add new room (new room dialog)
# delete current room (set current room to none, show all rooms)
# add/remove objects from room... (show object list)
# [X] list only objects in current room

# TODO object menu:
# spawn object... (show class list)
# select objects... (show object list)
# duplicate selected objects
# edit art for selected... (go to art mode)
# edit selected's room list... (go to room list)

class GameMenuData(PulldownMenuData):
    items = [HideEditUIMenuItem, ToggleGameModeMenuItem]

class GameRoomMenuData(PulldownMenuData):
    items = [FileNewMenuItem]

class GameObjectMenuData(PulldownMenuData):
    items = [SelectObjectsMenuItem]
