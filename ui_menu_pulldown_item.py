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
    # if True, item will never be dimmed
    always_active = False
    # if True, pulldown will close when this item is selected
    close_on_select = False
    def should_dim(app):
        "returns True if this item should be dimmed based on current application state"
        # so many commands are inapplicable with no active art, default to dimming an
        # item if this is the case
        return app.ui.active_art is None
    def get_label(app):
        "returns custom generated label based on app state"
        return None

class SeparatorItem(PulldownMenuItem):
    "menu separator, non-interactive and handled specially by menu drawing"
    pass

#
# file menu
#
class FileNewItem(PulldownMenuItem):
    label = 'New…'
    command = 'new_art'
    always_active = True

class FileOpenItem(PulldownMenuItem):
    label = 'Open…'
    command = 'open_art'
    always_active = True

class FileSaveItem(PulldownMenuItem):
    label = 'Save'
    command = 'save_current'
    def should_dim(app):
        return not app.ui.active_art or not app.ui.active_art.unsaved_changes

class FileSaveAsItem(PulldownMenuItem):
    label = 'Save As…'
    command = 'save_art_as'
    def should_dim(app):
        return app.ui.active_art is None

class FileCloseItem(PulldownMenuItem):
    label = 'Close'
    command = 'close_art'
    def should_dim(app):
        return app.ui.active_art is None

class FileRevertItem(PulldownMenuItem):
    label = 'Revert'
    command = 'revert_art'
    def should_dim(app):
        return app.ui.active_art is None or not app.ui.active_art.unsaved_changes

class FileImportItem(PulldownMenuItem):
    label = 'Import…'
    command = 'import_file'
    always_active = True

class FileExportItem(PulldownMenuItem):
    label = 'Export…'
    command = 'export_file'
    def should_dim(app):
        return app.ui.active_art is None

class FileExportLastItem(PulldownMenuItem):
    label = 'Export last'
    command = 'export_file_last'
    def should_dim(app):
        return app.ui.active_art is None

class FileConvertImageItem(PulldownMenuItem):
    label = 'Convert Image…'
    command = 'convert_image'
    def should_dim(app):
        return app.ui.active_art is None

class FileQuitItem(PulldownMenuItem):
    label = 'Quit'
    command = 'quit'
    always_active = True

#
# edit menu
#
class EditUndoItem(PulldownMenuItem):
    label = 'Undo'
    command = 'undo'
    def should_dim(app):
        return not app.ui.active_art or len(app.ui.active_art.command_stack.undo_commands) == 0

class EditRedoItem(PulldownMenuItem):
    label = 'Redo'
    command = 'redo'
    def should_dim(app):
        return not app.ui.active_art or len(app.ui.active_art.command_stack.redo_commands) == 0

class EditCutItem(PulldownMenuItem):
    label = 'Cut'
    command = 'cut_selection'
    def should_dim(app):
        return len(app.ui.select_tool.selected_tiles) == 0

class EditCopyItem(PulldownMenuItem):
    label = 'Copy'
    command = 'copy_selection'
    def should_dim(app):
        return len(app.ui.select_tool.selected_tiles) == 0

class EditPasteItem(PulldownMenuItem):
    label = 'Paste'
    command = 'select_paste_tool'
    def should_dim(app):
        return len(app.ui.clipboard) == 0

class EditDeleteItem(PulldownMenuItem):
    label = 'Clear'
    command = 'erase_selection_or_art'

class EditSelectAllItem(PulldownMenuItem):
    label = 'Select All'
    command = 'select_all'

class EditSelectNoneItem(PulldownMenuItem):
    label = 'Select None'
    command = 'select_none'

class EditSelectInvertItem(PulldownMenuItem):
    label = 'Invert Selection'
    command = 'select_invert'

#
# tool menu
#

class ToolTogglePickerItem(PulldownMenuItem):
    # two spaces in front of each label to leave room for mark
    label = 'Show char/color picker'
    command = 'toggle_picker'

class ToolTogglePickerHoldItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_picker_hold'
    def get_label(app):
        return 'Picker toggle key: %s' % ['press', 'hold'][app.ui.popup_hold_to_show]

class ToolPaintItem(PulldownMenuItem):
    # two spaces in front of each label to leave room for mark
    label = '  %s' % PencilTool.button_caption
    command = 'select_pencil_tool'

class ToolEraseItem(PulldownMenuItem):
    label = '  %s' % EraseTool.button_caption
    command = 'select_erase_tool'

class ToolRotateItem(PulldownMenuItem):
    label = '  %s' % RotateTool.button_caption
    command = 'select_rotate_tool'

class ToolGrabItem(PulldownMenuItem):
    label = '  %s' % GrabTool.button_caption
    command = 'select_grab_tool'

class ToolTextItem(PulldownMenuItem):
    label = '  %s' % TextTool.button_caption
    command = 'select_text_tool'

class ToolSelectItem(PulldownMenuItem):
    label = '  %s' % SelectTool.button_caption
    command = 'select_select_tool'

class ToolPasteItem(PulldownMenuItem):
    label = '  %s' % PasteTool.button_caption
    command = 'select_paste_tool'

class ToolIncreaseBrushSizeItem(PulldownMenuItem):
    label = 'blah'
    command = 'increase_brush_size'
    def should_dim(app):
        # dim this item for tools where brush size doesn't apply
        if not app.ui.active_art or not app.ui.selected_tool.brush_size:
            return True
    def get_label(app):
        if not app.ui.selected_tool.brush_size:
            return 'Increase brush size'
        size = app.ui.selected_tool.brush_size + 1
        return 'Increase brush size to %s' % size

class ToolDecreaseBrushSizeItem(PulldownMenuItem):
    label = 'blah'
    command = 'decrease_brush_size'
    def should_dim(app):
        if not app.ui.active_art or not app.ui.selected_tool.brush_size:
            return True
        return app.ui.selected_tool.brush_size <= 1
    def get_label(app):
        if not app.ui.selected_tool.brush_size:
            return 'Decrease brush size'
        size = app.ui.selected_tool.brush_size - 1
        return 'Decrease brush size to %s' % size

class ToolSettingsItem(PulldownMenuItem):
    # base class for tool settings toggle items
    def should_dim(app):
        # blacklist specific tools
        return not app.ui.active_art or type(app.ui.selected_tool) in [SelectTool]

class ToolToggleAffectsCharItem(ToolSettingsItem):
    label = '  Affects: character'
    command = 'toggle_affects_char'
    def should_mark(ui):
        return ui.selected_tool.affects_char

class ToolToggleAffectsFGItem(ToolSettingsItem):
    label = '  Affects: foreground color'
    command = 'toggle_affects_fg'
    def should_mark(ui):
        return ui.selected_tool.affects_fg_color

class ToolToggleAffectsBGItem(ToolSettingsItem):
    label = '  Affects: background color'
    command = 'toggle_affects_bg'
    def should_mark(ui):
        return ui.selected_tool.affects_bg_color

class ToolToggleAffectsXformItem(ToolSettingsItem):
    label = '  Affects: character xform'
    command = 'toggle_affects_xform'
    def should_mark(ui):
        return ui.selected_tool.affects_xform

#
# view  menu
#
class ViewToggleCRTItem(PulldownMenuItem):
    label = '  CRT filter'
    command = 'toggle_crt'
    def should_dim(app):
        return app.fb.disable_crt
    def should_mark(ui):
        return ui.app.fb.crt

class ViewToggleGridItem(PulldownMenuItem):
    label = '  Grid'
    command = 'toggle_grid_visibility'
    def should_mark(ui):
        return ui.app.grid.visible

class ViewToggleZoomExtentsItem(PulldownMenuItem):
    label = '  Zoom to Art extents'
    command = 'toggle_zoom_extents'
    def should_mark(ui):
        return ui.app.camera.zoomed_extents

class ViewZoomInItem(PulldownMenuItem):
    label = 'Zoom in'
    command = 'camera_zoom_in_proportional'

class ViewZoomOutItem(PulldownMenuItem):
    label = 'Zoom out'
    command = 'camera_zoom_out_proportional'

class ViewSetZoomItem(PulldownMenuItem):
    label = 'Set camera zoom…'
    command = 'set_camera_zoom'

class ViewToggleCameraTiltItem(PulldownMenuItem):
    label = '  Camera tilt'
    command = 'toggle_camera_tilt'
    always_active = True
    def should_mark(ui):
        return ui.app.camera.y_tilt != 0

#
# art menu
#
class ArtOpenAllGameAssetsItem(PulldownMenuItem):
    label = 'Open all Game Mode assets'
    command = 'open_all_game_assets'
    def should_dim(app):
        return len(app.gw.objects) == 0

class ArtPreviousItem(PulldownMenuItem):
    label = 'Previous Art'
    command = 'previous_art'
    def should_dim(app):
        return len(app.art_loaded_for_edit) < 2

class ArtNextItem(PulldownMenuItem):
    label = 'Next Art'
    command = 'next_art'
    def should_dim(app):
        return len(app.art_loaded_for_edit) < 2

class ArtCropToSelectionItem(PulldownMenuItem):
    label = 'Crop to selection'
    command = 'crop_to_selection'
    def should_dim(app):
        return len(app.ui.select_tool.selected_tiles) == 0

class ArtResizeItem(PulldownMenuItem):
    label = 'Resize…'
    command = 'resize_art'

#
# frame menu
#
class FramePreviousItem(PulldownMenuItem):
    label = 'Previous frame'
    command = 'previous_frame'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2

class FrameNextItem(PulldownMenuItem):
    label = 'Next frame'
    command = 'next_frame'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2

class FrameTogglePlaybackItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_anim_playback'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2
    def get_label(app):
        if not app.ui.active_art:
            return 'Start animation playback'
        animating = app.ui.active_art.renderables[0].animating
        return ['Start', 'Stop'][animating] + ' animation playback'

class FrameToggleOnionItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_onion_visibility'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2
    def get_label(app):
        l = '%s onion skin frames' % ['Show', 'Hide'][app.onion_frames_visible]
        return l

class FrameCycleOnionFramesItem(PulldownMenuItem):
    label = 'blah'
    command = 'cycle_onion_frames'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2
    def get_label(app):
        return 'Number of onion frames: %s' % app.onion_show_frames

class FrameCycleOnionDisplayItem(PulldownMenuItem):
    label = 'blah'
    command = 'cycle_onion_ahead_behind'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.frames < 2
    def get_label(app):
        if app.onion_show_frames_behind and app.onion_show_frames_ahead:
            display = 'Next & Previous'
        elif app.onion_show_frames_behind:
            display = 'Previous'
        else:
            display = 'Next'
        return 'Onion frames show: %s' % display

class FrameAddFrameItem(PulldownMenuItem):
    label = 'Add frame…'
    command = 'add_frame'

class FrameDuplicateFrameItem(PulldownMenuItem):
    label = 'Duplicate this frame…'
    command = 'duplicate_frame'

class FrameChangeDelayItem(PulldownMenuItem):
    label = "Change this frame's hold time…"
    command = 'change_frame_delay'

class FrameChangeDelayAllItem(PulldownMenuItem):
    label = "Change all frames' hold times…"
    command = 'change_frame_delay_all'

class FrameChangeIndexItem(PulldownMenuItem):
    label = "Change this frame's index…"
    command = 'change_frame_index'

class FrameDeleteFrameItem(PulldownMenuItem):
    label = 'Delete this frame'
    command = 'delete_frame'
    def should_dim(app):
        # don't delete last frame
        return not app.ui.active_art or app.ui.active_art.frames < 2

#
# layer menu
#
class LayerAddItem(PulldownMenuItem):
    label = "Add layer…"
    command = 'add_layer'

class LayerDuplicateItem(PulldownMenuItem):
    label = "Duplicate this layer…"
    command = 'duplicate_layer'

class LayerSetNameItem(PulldownMenuItem):
    label = "Change this layer's name…"
    command = 'change_layer_name'

class LayerSetZItem(PulldownMenuItem):
    label = "Change this layer's Z-depth…"
    command = 'change_layer_z'

class LayerToggleVisibleItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_layer_visibility'
    def get_label(app):
        if not app.ui.active_art:
            return 'Show this layer (Game Mode)'
        visible = app.ui.active_art.layers_visibility[app.ui.active_art.active_layer]
        return ['Show', 'Hide'][visible] + ' this layer (Game Mode)'

class LayerDeleteItem(PulldownMenuItem):
    label = "Delete this layer"
    command = 'delete_layer'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.layers < 2

class LayerSetInactiveVizItem(PulldownMenuItem):
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

class LayerShowHiddenItem(PulldownMenuItem):
    label = 'blah'
    command = 'toggle_hidden_layers_visible'
    def get_label(app):
        l = 'Art Mode-only layers: '
        l += ['Hidden', 'Visible'][app.show_hidden_layers]
        return l

class LayerPreviousItem(PulldownMenuItem):
    label = 'Previous layer'
    command = 'previous_layer'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.layers < 2

class LayerNextItem(PulldownMenuItem):
    label = 'Next layer'
    command = 'next_layer'
    def should_dim(app):
        return not app.ui.active_art or app.ui.active_art.layers < 2

#
# char/color menu
#
class ChooseCharSetItem(PulldownMenuItem):
    label = 'Choose character set…'
    command = 'choose_charset'

class ChoosePaletteItem(PulldownMenuItem):
    label = 'Choose palette…'
    command = 'choose_palette'

class PaletteFromImageItem(PulldownMenuItem):
    label = 'Palette from image…'
    command = 'palette_from_file'
    always_active = True

#
# help menu
#
class HelpDocsItem(PulldownMenuItem):
    label = 'Help (in browser)'
    command = 'open_help_docs'
    always_active = True
    close_on_select = True

class HelpGenerateDocsItem(PulldownMenuItem):
    label = 'Generate documentation'
    command = 'generate_docs'
    always_active = True
    close_on_select = True

class HelpWebsiteItem(PulldownMenuItem):
    label = 'Playscii website'
    command = 'open_website'
    always_active = True
    close_on_select = True

#
# menu data
#
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
    items = [FileNewItem, FileOpenItem, FileSaveItem, FileSaveAsItem,
             FileCloseItem, FileRevertItem, SeparatorItem, FileImportItem,
             FileExportItem, FileExportLastItem, SeparatorItem, FileQuitItem]

class EditMenuData(PulldownMenuData):
    items = [EditUndoItem, EditRedoItem, SeparatorItem,
             EditCutItem, EditCopyItem, EditPasteItem, EditDeleteItem,
             SeparatorItem, EditSelectAllItem,
             EditSelectNoneItem, EditSelectInvertItem]

class ToolMenuData(PulldownMenuData):
    items = [ToolTogglePickerItem, ToolTogglePickerHoldItem, SeparatorItem,
             ToolPaintItem, ToolEraseItem, ToolRotateItem, ToolGrabItem,
             ToolTextItem, ToolSelectItem, ToolPasteItem, SeparatorItem,
             ToolIncreaseBrushSizeItem, ToolDecreaseBrushSizeItem,
             ToolToggleAffectsCharItem, ToolToggleAffectsFGItem,
             ToolToggleAffectsBGItem, ToolToggleAffectsXformItem]
             # TODO: cycle char/color/xform items?
    # TODO: generate list from UI.tools instead of manually specified MenuItems
    def should_mark_item(item, ui):
        # if it's a tool setting toggle, use its own mark check function
        if item.__bases__[0] is ToolSettingsItem:
            return item.should_mark(ui)
        return item.label == '  %s' % ui.selected_tool.button_caption

class ViewMenuData(PulldownMenuData):
    items = [ViewToggleCRTItem, ViewToggleGridItem, SeparatorItem,
             ViewToggleZoomExtentsItem, ViewZoomInItem, ViewZoomOutItem,
             ViewSetZoomItem, ViewToggleCameraTiltItem]
    
    def should_mark_item(item, ui):
        if hasattr(item, 'should_mark'):
            return item.should_mark(ui)
        return False

class ArtMenuData(PulldownMenuData):
    items = [ArtResizeItem, ArtCropToSelectionItem, SeparatorItem,
             ArtOpenAllGameAssetsItem, SeparatorItem,
             ArtPreviousItem, ArtNextItem, SeparatorItem]
    
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
    items = [FrameAddFrameItem, FrameDuplicateFrameItem,
             FrameChangeDelayItem, FrameChangeDelayAllItem,
             FrameChangeIndexItem, FrameDeleteFrameItem, SeparatorItem,
             FrameTogglePlaybackItem, FramePreviousItem, FrameNextItem,
             SeparatorItem,
             FrameToggleOnionItem, FrameCycleOnionFramesItem,
             FrameCycleOnionDisplayItem]


class LayerMenuData(PulldownMenuData):
    
    items = [LayerAddItem, LayerDuplicateItem, LayerSetNameItem, LayerSetZItem,
             LayerDeleteItem, SeparatorItem,
             LayerSetInactiveVizItem, LayerPreviousItem,LayerNextItem,
             SeparatorItem, LayerToggleVisibleItem, LayerShowHiddenItem,
             SeparatorItem]
    
    def should_mark_item(item, ui):
        "show checkmark for active art"
        if not ui.active_art:
            return False
        return ui.active_art.active_layer == item.cb_arg
    
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
            if not app.ui.active_art.layers_visibility[i]:
                item.label += ' (hidden)'
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
    items = [ChooseCharSetItem, ChoosePaletteItem, SeparatorItem,
             PaletteFromImageItem]

class HelpMenuData(PulldownMenuData):
    items = [HelpDocsItem, HelpGenerateDocsItem, HelpWebsiteItem]
