import time

class EditCommand:
    
    "undo/redo-able representation of an art edit (eg paint, erase) operation"
    
    def __init__(self, art):
        self.art = art
        self.start_time = art.app.elapsed_time
        self.finish_time = None
        # nested dictionary with frame(layer(column(row))) structure -
        # this prevents multiple commands operating on the same tile
        # from stomping each other
        self.tile_commands = {}
    
    def get_number_of_commands(self):
        commands = 0
        for frame in self.tile_commands.values():
            for layer in frame.values():
                for column in layer.values():
                    for tile in column.values():
                        commands += 1
        return commands
    
    def __str__(self):
        # get unique-ish ID from memory address
        addr = self.__repr__()
        addr = addr[addr.find('0'):-1]
        s = 'EditCommand_%s: %s tiles, time %s' % (addr, self.get_number_of_commands(),
                                                   self.finish_time)
        return s
    
    def add_command_tiles(self, new_command_tiles):
        for ct in new_command_tiles:
            # create new tables for frames/layers/columns if not present
            if not ct.frame in self.tile_commands:
                self.tile_commands[ct.frame] = {}
            if not ct.layer in self.tile_commands[ct.frame]:
                self.tile_commands[ct.frame][ct.layer] = {}
            if not ct.y in self.tile_commands[ct.frame][ct.layer]:
                self.tile_commands[ct.frame][ct.layer][ct.y] = {}
            # preserve "before" state of any command we overwrite
            if ct.x in self.tile_commands[ct.frame][ct.layer][ct.y]:
                old_ct = self.tile_commands[ct.frame][ct.layer][ct.y][ct.x]
                ct.set_before(old_ct.b_char, old_ct.b_fg, old_ct.b_bg,
                              old_ct.b_xform)
            self.tile_commands[ct.frame][ct.layer][ct.y][ct.x] = ct
    
    def undo_commands_for_tile(self, frame, layer, x, y):
        self.tile_commands[frame][layer][y][x].undo()
    
    def undo(self):
        for frame in self.tile_commands.values():
            for layer in frame.values():
                for column in layer.values():
                    for tile_command in column.values():
                        tile_command.undo()
    
    def apply(self):
        for frame in self.tile_commands.values():
            for layer in frame.values():
                for column in layer.values():
                    for tile_command in column.values():
                        tile_command.apply()


class ResizeCommand:
    
    "undo/redo-able representation of an art resize/crop operation"
    
    # art arrays to grab
    array_types = ['chars', 'fg_colors', 'bg_colors', 'uv_mods']
    
    def __init__(self, art, origin_x=0, origin_y=0):
        self.art = art
        # remember origin of resize command
        self.origin_x, self.origin_y = origin_x, origin_y
        self.start_time = self.finish_time = art.app.elapsed_time
    
    def save_tiles(self, before=True):
        # save copies of tile data lists
        prefix = 'b' if before else 'a'
        for atype in self.array_types:
            # save list as eg "b_chars" for "character data before operation"
            src_data = getattr(self.art, atype)
            var_name = '%s_%s' % (prefix, atype)
            setattr(self, var_name, src_data[:])
        if before:
            self.before_size = (self.art.width, self.art.height)
        else:
            self.after_size = (self.art.width, self.art.height)
    
    def undo(self):
        x, y = self.before_size
        self.art.resize(x, y, self.origin_x, self.origin_y)
        for atype in self.array_types:
            new_data = getattr(self, 'b_' + atype)
            setattr(self.art, atype, new_data[:])
        # Art.resize will set geo_changed and mark all frames changed
        self.art.app.ui.adjust_for_art_resize(self.art)
    
    def apply(self):
        x, y = self.after_size
        self.art.resize(x, y, self.origin_x, self.origin_y)
        for atype in self.array_types:
            new_data = getattr(self, 'a_' + atype)
            setattr(self.art, atype, new_data[:])
        self.art.app.ui.adjust_for_art_resize(self.art)


class EditCommandTile:
    
    serialized_items = ['frame', 'layer', 'x', 'y',
                        'b_char', 'b_fg', 'b_bg', 'b_xform',
                        'a_char', 'a_fg', 'a_bg', 'a_xform']
    
    def __init__(self, art):
        self.art = art
        self.creation_time = self.art.app.elapsed_time
        # initialize everything
        for item in self.serialized_items:
            setattr(self, item, None)
    
    def __str__(self):
        s = 'F%s L%s %s,%s @ %.2f: ' % (self.frame, self.layer, str(self.x).rjust(2, '0'), str(self.y).rjust(2, '0'), self.creation_time)
        s += 'c%s f%s b%s x%s -> ' % (self.b_char, self.b_fg, self.b_bg, self.b_xform)
        s += 'c%s f%s b%s x%s' % (self.a_char, self.a_fg, self.a_bg, self.a_xform)
        return s
    
    def __eq__(self, value):
        for item in self.serialized_items:
            if getattr(self, item) != getattr(value, item):
                return False
        return True
    
    def copy(self):
        "returns a deep copy of this tile command"
        new_ect = EditCommandTile(self.art)
        # TODO: old or new timestamp? does it matter?
        new_ect.creation_time = self.art.app.elapsed_time
        for item in self.serialized_items:
            setattr(new_ect, item, getattr(self, item))
        return new_ect
    
    def set_tile(self, frame, layer, x, y):
        self.frame, self.layer = frame, layer
        self.x, self.y = x, y
    
    def set_before(self, char, fg, bg, xform):
        self.b_char, self.b_xform = char, xform
        self.b_fg, self.b_bg = fg, bg
    
    def set_after(self, char, fg, bg, xform):
        self.a_char, self.a_xform = char, xform
        self.a_fg, self.a_bg = fg, bg
    
    def is_null(self):
        return self.a_char == self.b_char and self.a_fg == self.b_fg and self.a_bg == self.b_bg and self.a_xform == self.b_xform
    
    def undo(self):
        if self.x >= self.art.width or self.y >= self.art.height:
            return
        self.art.set_tile_at(self.frame, self.layer, self.x, self.y,
                             self.b_char, self.b_fg, self.b_bg, self.b_xform)
    
    def apply(self):
        self.art.set_tile_at(self.frame, self.layer, self.x, self.y,
                             self.a_char, self.a_fg, self.a_bg, self.a_xform)


class CommandStack:
    
    def __init__(self, art):
        self.art = art
        self.undo_commands, self.redo_commands = [], []
    
    def __str__(self):
        s = 'stack for %s:\n' % self.art.filename
        s += '===\nundo:\n'
        for cmd in self.undo_commands:
            s += str(cmd) + '\n'
        s += '\n===\nredo:\n'
        for cmd in self.redo_commands:
            s += str(cmd) + '\n'
        return s
    
    def commit_commands(self, new_commands):
        self.undo_commands += new_commands[:]
        self.clear_redo()
    
    def undo(self):
        if len(self.undo_commands) == 0:
            return
        command = self.undo_commands.pop()
        self.art.app.cursor.undo_preview_edits()
        command.undo()
        self.redo_commands.append(command)
        self.art.app.cursor.update_cursor_preview()
    
    def redo(self):
        if len(self.redo_commands) == 0:
            return
        command = self.redo_commands.pop()
        # un-apply cursor preview before applying redo, else preview edits
        # edits will "stick"
        self.art.app.cursor.undo_preview_edits()
        command.apply()
        # add to end of undo stack
        self.undo_commands.append(command)
        self.art.app.cursor.update_cursor_preview()
    
    def clear_redo(self):
        self.redo_commands = []
