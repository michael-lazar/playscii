import time

FUDGE = 0.1

class EditCommand:
    
    def __init__(self, art):
        self.art = art
        # creation timestamp
        self.creation_time = time.time()
        # last left click time
        # TODO: this might be better to do in whatever code is creating us?
        self.last_click_time = self.art.app.last_click_times.get(1, 99999999999999)
    
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


# time (in seconds) range within which 
COMMAND_INTERVAL = 3

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
        self.undo_commands += new_commands
    
    def get_recent_commands(self):
        commands = []
        # TODO: replace with "get_commands_since_time"
        return commands
    
    def get_commands_since_last_click(self, command_list, before=False):
        commands = []
        last_click = command_list[-1].last_click_time
        for command in command_list:
            if not before and command.last_click_time >= last_click - FUDGE:
                commands.append(command)
            elif before and command.last_click_time <= last_click + FUDGE:
                commands.append(command)
        return commands
    
    def undo_since_interval(self):
        pass
    
    def undo_since_last_click(self):
        commands = self.get_commands_since_last_click(self.undo_commands)
        for command in commands:
            self.undo_commands.remove(command)
            command.undo()
            self.redo_commands.append(command)
        #print('undid %s commands' % len(commands))
    
    def redo_since_last_click(self):
        commands = self.get_commands_since_last_click(self.redo_commands, True)
        for command in commands:
            self.redo_commands.remove(command)
            command.apply()
            self.undo_commands.append(command)
        #print('redid %s commands' % len(commands))
    
    def undo(self):
        if len(self.undo_commands) == 0:
            return
        if self.art.app.ui.selected_tool.paint_while_dragging:
            self.undo_since_last_click()
    
    def redo(self):
        # TODO: find >=1 redo_commands to redo, pop them off end of list,
        # add them to undo_commands
        if len(self.redo_commands) == 0:
            return
        if self.art.app.ui.selected_tool.paint_while_dragging:
            self.redo_since_last_click()
    
    def clear_redo(self):
        self.redo_commands = []
