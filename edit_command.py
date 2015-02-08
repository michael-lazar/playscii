import time

class EditCommand:
    
    def __init__(self, art):
        self.art = art
        self.start_time = art.app.elapsed_time
        self.finish_time = None
        self.tile_commands = []
    
    def add_command_tiles(self, new_command_tiles):
        "add one or more command tiles"
        # check type to support one command or a list of commands
        if type(new_command_tiles) is EditCommandTile:
            self.tile_commands.append(new_command_tiles)
        else:
            self.tile_commands += new_command_tiles[:]
    
    def undo_commands_for_tile(self, frame, layer, x, y):
        for tc in self.tile_commands:
            if tc.frame == frame and tc.layer == layer and tc.x == x and tc.y == y:
                tc.undo()
    
    def undo(self):
        for tile_command in self.tile_commands:
            tile_command.undo()
    
    def apply(self):
        for tile_command in self.tile_commands:
            tile_command.apply()


class EditCommandTile:
    
    def __init__(self, art):
        self.art = art
        self.creation_time = self.art.app.elapsed_time
    
    def __str__(self):
        s = 'F%s L%s %s,%s @ %.2f: ' % (self.frame, self.layer, str(self.x).rjust(2, '0'), str(self.y).rjust(2, '0'), self.creation_time)
        s += 'c%s f%s b%s x%s -> ' % (self.b_char, self.b_fg, self.b_bg, self.b_xform)
        s += 'c%s f%s b%s x%s' % (self.a_char, self.a_fg, self.a_bg, self.a_xform)
        return s
    
    def __eq__(self, value):
        items = ['frame', 'layer', 'x', 'y',
                 'b_char', 'b_fg', 'b_bg', 'b_xform',
                 'a_char', 'a_fg', 'a_bg', 'a_xform']
        for item in items:
            if getattr(self, item) != getattr(value, item):
                return False
        return True
    
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
        # check type to support one command or a list of commands
        if type(new_commands) is EditCommand:
            self.undo_commands.append(new_commands)
        else:
            self.undo_commands += new_commands[:]
    
    def undo(self):
        if len(self.undo_commands) == 0:
            return
        command = self.undo_commands.pop()
        command.undo()
        self.redo_commands.append(command)
    
    def redo(self):
        if len(self.redo_commands) == 0:
            return
        command = self.redo_commands.pop()
        command.apply()
        self.undo_commands.append(command)
    
    def clear_redo(self):
        # TODO: when should this be invoked?
        self.redo_commands = []
