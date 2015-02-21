
from ui_tool import PencilTool, EraseTool, RotateTool, GrabTool, TextTool, SelectTool, PasteTool

#
# specific pulldown menu items, eg File > Save, Edit > Copy
#

class PulldownMenuItem:
    # label that displays for this item
    label = 'Test Menu Item'
    # bindable command we look up from InputLord to get binding text from
    command = 'test_command'
    def should_dim(app):
        "returns True if this item should be dimmed based on current application state"
        # so many commands are inapplicable with no active art, default to dimming an
        # item if this is the case
        return app.ui.active_art is None

class SeparatorMenuItem(PulldownMenuItem):
    "menu separator, non-interactive and handled specially by menu drawing"
    pass

class FileNewMenuItem(PulldownMenuItem):
    label = 'New...'
    command = 'new_art'
    def should_dim(app):
        return False

class FileOpenMenuItem(PulldownMenuItem):
    label = 'Open...'
    command = 'open_art'
    def should_dim(app):
        return False

class FileSaveMenuItem(PulldownMenuItem):
    label = 'Save'
    command = 'save_art'
    def should_dim(app):
        return not app.ui.active_art or not app.ui.active_art.unsaved_changes

class FileSaveAsMenuItem(PulldownMenuItem):
    label = 'Save As...'
    command = 'save_art_as'
    def should_dim(app):
        return app.ui.active_art is None

class FileCloseMenuItem(PulldownMenuItem):
    label = 'Close'
    command = 'close_art'
    def should_dim(app):
        return app.ui.active_art is None

class FilePNGExportMenuItem(PulldownMenuItem):
    label = 'Export PNG'
    command = 'export_image'
    def should_dim(app):
        return app.ui.active_art is None

class FileQuitMenuItem(PulldownMenuItem):
    label = 'Quit'
    command = 'quit'
    def should_dim(app):
        return False

class EditUndoMenuItem(PulldownMenuItem):
    label = 'Undo'
    command = 'undo'
    def should_dim(app):
        return not app.ui.active_art or len(app.ui.active_art.command_stack.undo_commands) == 0

class EditRedoMenuItem(PulldownMenuItem):
    label = 'Redo'
    command = 'redo'
    def should_dim(app):
        return not app.ui.active_art or len(app.ui.active_art.command_stack.redo_commands) == 0

class EditCutMenuItem(PulldownMenuItem):
    label = 'Cut'
    command = 'cut_selection'
    def should_dim(app):
        return len(app.ui.select_tool.selected_tiles) == 0

class EditCopyMenuItem(PulldownMenuItem):
    label = 'Copy'
    command = 'copy_selection'
    def should_dim(app):
        return len(app.ui.select_tool.selected_tiles) == 0

class EditPasteMenuItem(PulldownMenuItem):
    label = 'Paste'
    command = 'select_paste_tool'
    def should_dim(app):
        return len(app.ui.clipboard) == 0

class EditDeleteMenuItem(PulldownMenuItem):
    label = 'Clear'
    command = 'erase_selection_or_art'

class EditSelectAllMenuItem(PulldownMenuItem):
    label = 'Select All'
    command = 'select_all'

class EditSelectNoneMenuItem(PulldownMenuItem):
    label = 'Select None'
    command = 'select_none'

class EditSelectInvertMenuItem(PulldownMenuItem):
    label = 'Invert Selection'
    command = 'select_invert'

class ToolPaintMenuItem(PulldownMenuItem):
    # two spaces in front of each label to leave room for mark
    label = '  %s' % PencilTool.button_caption
    command = 'select_pencil_tool'

class ToolEraseMenuItem(PulldownMenuItem):
    label = '  %s' % EraseTool.button_caption
    command = 'select_erase_tool'

class ToolRotateMenuItem(PulldownMenuItem):
    label = '  %s' % RotateTool.button_caption
    command = 'select_rotate_tool'

class ToolGrabMenuItem(PulldownMenuItem):
    label = '  %s' % GrabTool.button_caption
    command = 'select_grab_tool'

class ToolTextMenuItem(PulldownMenuItem):
    label = '  %s' % TextTool.button_caption
    command = 'select_text_tool'

class ToolSelectMenuItem(PulldownMenuItem):
    label = '  %s' % SelectTool.button_caption
    command = 'select_select_tool'

class ToolPasteMenuItem(PulldownMenuItem):
    label = '  %s' % PasteTool.button_caption
    command = 'select_paste_tool'

class ArtPreviousMenuItem(PulldownMenuItem):
    label = 'Previous Art'
    command = 'previous_art'
    def should_dim(app):
        return len(app.art_loaded_for_edit) < 2

class ArtNextMenuItem(PulldownMenuItem):
    label = 'Next Art'
    command = 'next_art'
    def should_dim(app):
        return len(app.art_loaded_for_edit) < 2

class FramePreviousMenuItem(PulldownMenuItem):
    label = 'Previous frame'
    command = 'previous_frame'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2

class FrameNextMenuItem(PulldownMenuItem):
    label = 'Next frame'
    command = 'next_frame'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2

class LayerPreviousMenuItem(PulldownMenuItem):
    label = 'Previous layer'
    command = 'previous_layer'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.layers < 2

class LayerNextMenuItem(PulldownMenuItem):
    label = 'Next layer'
    command = 'next_layer'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.layers < 2

class HelpScreenMenuItem(PulldownMenuItem):
    label = 'Help...'
    command = 'open_help_screen'
    def should_dim(app):
        # there is always help <3
        return False

class HelpReadmeMenuItem(PulldownMenuItem):
    label = 'Open README'
    command = 'open_readme'
    def should_dim(app):
        return False

class PulldownMenuData:
    "data for pulldown menus, eg File, Edit, etc; mainly a list of menu items"
    items = []
    def should_mark_item(item, ui):
        "returns True if this item should be marked, subclasses have custom logic here"
        return False

class FileMenuData(PulldownMenuData):
    items = [FileNewMenuItem, FileOpenMenuItem, FileSaveMenuItem, FileSaveAsMenuItem,
             FileCloseMenuItem, FilePNGExportMenuItem, SeparatorMenuItem,
             FileQuitMenuItem]

class EditMenuData(PulldownMenuData):
    items = [EditUndoMenuItem, EditRedoMenuItem, SeparatorMenuItem,
             EditCutMenuItem, EditCopyMenuItem, EditPasteMenuItem,
             EditDeleteMenuItem, SeparatorMenuItem, EditSelectAllMenuItem,
             EditSelectNoneMenuItem, EditSelectInvertMenuItem]

class ToolMenuData(PulldownMenuData):
    items = [ToolPaintMenuItem, ToolEraseMenuItem, ToolRotateMenuItem, ToolGrabMenuItem,
             ToolTextMenuItem, ToolSelectMenuItem, ToolPasteMenuItem]
    # TODO: notion of "item list generator", function of custom logic that adds to /
    # replaces predefined item list
    def should_mark_item(item, ui):
        return item.label == '  %s' % ui.selected_tool.button_caption

class ArtMenuData(PulldownMenuData):
    items = [ArtPreviousMenuItem, ArtNextMenuItem]

class FrameMenuData(PulldownMenuData):
    items = [FramePreviousMenuItem, FrameNextMenuItem]

class LayerMenuData(PulldownMenuData):
    items = [LayerPreviousMenuItem, LayerNextMenuItem]

class HelpMenuData(PulldownMenuData):
    items = [HelpScreenMenuItem, HelpReadmeMenuItem]
