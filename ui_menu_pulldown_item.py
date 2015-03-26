
from renderable import LAYER_VIS_FULL, LAYER_VIS_DIM, LAYER_VIS_NONE

from ui_tool import PencilTool, EraseTool, RotateTool, GrabTool, TextTool, SelectTool, PasteTool

#
# specific pulldown menu items, eg File > Save, Edit > Copy
#

class PulldownMenuItem:
    # label that displays for this item
    label = 'Test Menu Item'
    # bindable command we look up from InputLord to get binding text from
    command = 'test_command'
    # if not None, passed to button's cb_arg
    cb_arg = None
    # if True, pulldown button creation process won't auto-pad
    no_pad = False
    def should_dim(app):
        "returns True if this item should be dimmed based on current application state"
        # so many commands are inapplicable with no active art, default to dimming an
        # item if this is the case
        return app.ui.active_art is None
    def get_label(app):
        "returns custom generated label based on app state"
        return None

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

class FileImportImageMenuItem(PulldownMenuItem):
    label = 'Import Image...'
    command = 'import_image'
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

class ArtCropToSelectionMenuItem(PulldownMenuItem):
    label = 'Crop to selection'
    command = 'crop_to_selection'
    def should_dim(app):
        return len(app.ui.select_tool.selected_tiles) == 0

class ArtResizeMenuItem(PulldownMenuItem):
    label = 'Resize...'
    command = 'resize_art'

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

class FrameTogglePlaybackMenuItem(PulldownMenuItem):
    label = 'Play/pause animation'
    command = 'toggle_anim_playback'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2

class FrameToggleOnionMenuitem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_onion_visibility'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2
    def get_label(app):
        l = 'Onion skin frames: '
        l += ['Hidden', 'Visible'][app.onion_frames_visible]
        return l

class FrameAddFrameMenuItem(PulldownMenuItem):
    label = 'Add frame...'
    command = 'add_frame'

class FrameDuplicateFrameMenuItem(PulldownMenuItem):
    label = 'Duplicate this frame...'
    command = 'duplicate_frame'

class FrameChangeDelayMenuItem(PulldownMenuItem):
    label = "Change this frame's hold time..."
    command = 'change_frame_delay'

class FrameChangeIndexMenuItem(PulldownMenuItem):
    label = "Change this frame's index..."
    command = 'change_frame_index'

class FrameDeleteFrameMenuItem(PulldownMenuItem):
    label = 'Delete this frame'
    command = 'delete_frame'
    def should_dim(app):
        # don't delete last frame
        return not app.ui.active_art or app.ui.active_art.frames < 2

class LayerAddMenuItem(PulldownMenuItem):
    label = "Add layer..."
    command = 'add_layer'

class LayerDuplicateMenuItem(PulldownMenuItem):
    label = "Duplicate this layer..."
    command = 'duplicate_layer'

class LayerSetNameMenuItem(PulldownMenuItem):
    label = "Change this layer's name..."
    command = 'change_layer_name'

class LayerSetZMenuItem(PulldownMenuItem):
    label = "Change this layer's Z-depth..."
    command = 'change_layer_z'

class LayerDeleteMenuItem(PulldownMenuItem):
    label = "Delete this layer"
    command = 'delete_layer'

class LayerSetInactiveVizMenuItem(PulldownMenuItem):
    label = 'blah'
    command = 'cycle_inactive_layer_visibility'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.layers < 2
    def get_label(app):
        l = 'Inactive layers: '
        if app.inactive_layer_visibility == LAYER_VIS_FULL:
            return l + 'Visible'
        elif app.inactive_layer_visibility == LAYER_VIS_DIM:
            return l + 'Dim'
        elif app.inactive_layer_visibility == LAYER_VIS_NONE:
            return l + 'Invisible'

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

class ChooseCharSetMenuItem(PulldownMenuItem):
    label = 'Choose character set...'
    command = 'choose_charset'

class ChoosePaletteMenuItem(PulldownMenuItem):
    label = 'Choose palette...'
    command = 'choose_palette'

class PaletteFromFileMenuItem(PulldownMenuItem):
    label = 'Palette from file...'
    command = 'palette_from_file'

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

class HelpWebsiteMenuItem(PulldownMenuItem):
    label = 'Playscii website'
    command = 'open_website'
    def should_dim(app):
        return False

class PulldownMenuData:
    "data for pulldown menus, eg File, Edit, etc; mainly a list of menu items"
    items = []
    def should_mark_item(item, ui):
        "returns True if this item should be marked, subclasses have custom logic here"
        return False
    def get_items(app):
        """
        returns a list of items generated from app state, used for
        dynamically-generated items
        """
        return []

class FileMenuData(PulldownMenuData):
    items = [FileNewMenuItem, FileOpenMenuItem, FileSaveMenuItem, FileSaveAsMenuItem,
             FileCloseMenuItem, FileImportImageMenuItem, FilePNGExportMenuItem,
             SeparatorMenuItem, FileQuitMenuItem]

class EditMenuData(PulldownMenuData):
    items = [EditUndoMenuItem, EditRedoMenuItem, SeparatorMenuItem,
             EditCutMenuItem, EditCopyMenuItem, EditPasteMenuItem,
             EditDeleteMenuItem, SeparatorMenuItem, EditSelectAllMenuItem,
             EditSelectNoneMenuItem, EditSelectInvertMenuItem]

class ToolMenuData(PulldownMenuData):
    items = [ToolPaintMenuItem, ToolEraseMenuItem, ToolRotateMenuItem, ToolGrabMenuItem,
             ToolTextMenuItem, ToolSelectMenuItem, ToolPasteMenuItem]
    # TODO: generate list from UI.tools instead of manually specified MenuItems
    def should_mark_item(item, ui):
        return item.label == '  %s' % ui.selected_tool.button_caption


class ArtMenuData(PulldownMenuData):
    items = [ArtResizeMenuItem, ArtCropToSelectionMenuItem, SeparatorMenuItem,
             ArtPreviousMenuItem, ArtNextMenuItem, SeparatorMenuItem]
    
    def should_mark_item(item, ui):
        "show checkmark for active art"
        return ui.active_art and ui.active_art.filename == item.cb_arg
    
    def get_items(app):
        "turn each loaded art into a menu item"
        items = []
        for art in app.art_loaded_for_edit:
            # class just being used to store data, no need to spawn it
            class TempMenuItemClass(PulldownMenuItem): pass
            item = TempMenuItemClass
            # leave spaces for mark
            item.label = '  %s' % art.filename
            item.command = 'art_switch_to'
            item.cb_arg = art.filename
            # order list by art's time loaded
            item.time_loaded = art.time_loaded
            items.append(item)
        items.sort(key=lambda item: item.time_loaded)
        return items


class FrameMenuData(PulldownMenuData):
    items = [FramePreviousMenuItem, FrameNextMenuItem,
             FrameTogglePlaybackMenuItem, FrameToggleOnionMenuitem,
             SeparatorMenuItem,
             FrameAddFrameMenuItem, FrameDuplicateFrameMenuItem,
             FrameChangeDelayMenuItem, FrameChangeIndexMenuItem,
             FrameDeleteFrameMenuItem]


class LayerMenuData(PulldownMenuData):
    
    items = [LayerAddMenuItem, LayerDuplicateMenuItem, LayerSetNameMenuItem,
             LayerSetZMenuItem, LayerDeleteMenuItem, SeparatorMenuItem,
             LayerSetInactiveVizMenuItem, LayerPreviousMenuItem,
             LayerNextMenuItem, SeparatorMenuItem]
    
    def should_mark_item(item, ui):
        "show checkmark for active art"
        return ui.active_layer == item.cb_arg
    
    def get_items(app):
        "turn each layer into a menu item"
        items = []
        if not app.ui.active_art:
            return items
        # first determine longest line to set width of items
        longest_line = 0
        for layer_name in app.ui.active_art.layer_names:
            if len(layer_name) > longest_line:
                longest_line = len(layer_name)
        # check non-generated menu items too
        for item in LayerMenuData.items:
            if len(item.label) + 1 > longest_line:
                longest_line = len(item.label) + 1
        # cap at max allowed line length
        longest_line = min(longest_line, 50)
        for i,layer_name in enumerate(app.ui.active_art.layer_names):
            class TempMenuItemClass(PulldownMenuItem): pass
            item = TempMenuItemClass
            # leave spaces for mark
            item.label = '  %s' % layer_name
            # pad, put Z depth on far right
            item.label = item.label.ljust(longest_line)
            # trim to keep below a max length
            item.label = item.label[:longest_line]
            # spaces between layer name and z depth
            item.label += 'z:%.2f' % app.ui.active_art.layers_z[i]
            # tell PulldownMenu's button creation process not to auto-pad
            item.no_pad = True
            item.command = 'layer_switch_to'
            item.cb_arg = i
            items.append(item)
        return items

class CharColorMenuData(PulldownMenuData):
    items = [ChooseCharSetMenuItem, ChoosePaletteMenuItem, SeparatorMenuItem, PaletteFromFileMenuItem]

class HelpMenuData(PulldownMenuData):
    items = [HelpScreenMenuItem, HelpReadmeMenuItem, HelpWebsiteMenuItem]
