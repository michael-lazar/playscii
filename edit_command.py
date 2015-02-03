import time

FUDGE = 0.1

class EditCommand:
    
    def __init__(self, art):
        self.art = art
        # creation timestamp
        self.time = time.time()
        # last left click time
        # TODO: this might be better to do in whatever code is creating us?
        self.click_time = self.art.app.last_click_times.get(1, 99999999999999)
    
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
    
    def commit_commands(self, new_commands):
        self.undo_commands += new_commands
    
    def get_recent_commands(self):
        commands = []
        # TODO: replace with "get_commands_since_time"
        return commands
    
    def get_commands_since_last_click(self, command_list, before=False):
        commands = []
        last_click = command_list[-1].click_time
        for command in command_list:
            if not before and command.click_time >= last_click - FUDGE:
                commands.append(command)
            elif before and command.click_time <= last_click + FUDGE:
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
