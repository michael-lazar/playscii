import math, ctypes
import numpy as np
from OpenGL import GL

from edit_command import EditCommand

"""
reference diagram:

    0       0.2             0.8      1.0
    A--------B               *--------*
    |        |               |        |
0.1 |  D-----C               *-----*  |
    |  |                           |  |
    |  |                           |  |
0.2 F--E                           *--*

etc
"""

OUTSIDE_EDGE_SIZE = 0.2
THICKNESS = 0.1

corner_verts = [
                    0, 0,                  # A/0
    OUTSIDE_EDGE_SIZE, 0,                  # B/1
    OUTSIDE_EDGE_SIZE, -THICKNESS,         # C/2
            THICKNESS, -THICKNESS,         # D/3
            THICKNESS, -OUTSIDE_EDGE_SIZE, # E/4
                    0, -OUTSIDE_EDGE_SIZE  # F/5
]

# vert indices for the above
corner_elems = [
    0, 1, 2,
    0, 2, 3,
    0, 3, 4,
    0, 5, 4
]

# X/Y flip transforms to make all 4 corners
# (top left, top right, bottom left, bottom right)
corner_transforms = [
    ( 1,  1),
    (-1,  1),
    ( 1, -1),
    (-1, -1)
]

# offsets to translate the 4 corners by
corner_offsets = [
    (0, 0),
    (1, 0),
    (0, -1),
    (1, -1)
]

BASE_COLOR = (0.8, 0.8, 0.8, 1)

# why do we use the weird transforms and offsets?
# because a static vertex list wouldn't be able to adjust to different
# character set aspect ratios.

class Cursor:
    
    vert_shader_source = 'cursor_v.glsl'
    frag_shader_source = 'cursor_f.glsl'
    alpha = 1
    logg = False
    
    def __init__(self, app):
        self.app = app
        self.x, self.y, self.z = 0, 0, 0
        self.last_x, self.last_y = 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        # list of EditCommandTiles for preview
        self.preview_edits = []
        self.current_command = None
        # offsets to render the 4 corners at
        self.mouse_x, self.mouse_y = 0, 0
        self.moved = False
        self.color = np.array(BASE_COLOR, dtype=np.float32)
        # GL objects
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.vert_buffer, self.elem_buffer = GL.glGenBuffers(2)
        self.vert_array = np.array(corner_verts, dtype=np.float32)
        self.elem_array = np.array(corner_elems, dtype=np.uint32)
        self.vert_count = int(len(self.elem_array))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_array.nbytes,
                        self.elem_array, GL.GL_STATIC_DRAW)
        # shader, attributes
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        # vert positions
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        # uniforms
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.color_uniform = self.shader.get_uniform_location('baseColor')
        self.quad_size_uniform = self.shader.get_uniform_location('quadSize')
        self.xform_uniform = self.shader.get_uniform_location('vertTransform')
        self.offset_uniform = self.shader.get_uniform_location('vertOffset')
        self.alpha_uniform = self.shader.get_uniform_location('baseAlpha')
        # finish
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
    
    def keyboard_move(self, delta_x, delta_y):
        self.x += delta_x
        self.y += delta_y
        self.moved = True
        self.app.keyboard_editing = True
        if self.logg:
            self.app.log('Cursor: %s,%s,%s scale %.2f,%.2f' % (self.x, self.y, self.z, self.scale_x, self.scale_y))
    
    def set_scale(self, new_scale):
        self.scale_x = self.scale_y = new_scale
    
    def get_tile(self):
        # adjust for brush size
        size = self.app.ui.selected_tool.brush_size
        if size:
            size_offset = math.ceil(size / 2) - 1
            return int(self.x + size_offset), int(-self.y + size_offset)
        else:
            return self.x, self.y
    
    def get_tiles_under_brush(self, base_zero=False):
        """
        returns list of tuple coordinates of all tiles under the cursor @ its
        current brush size
        """
        size = self.app.ui.selected_tool.brush_size
        tiles = []
        x_start, y_start = int(self.x), int(-self.y)
        if base_zero:
            x_start, y_start = 0, 0
        for y in range(y_start, y_start + size):
            for x in range(x_start, x_start + size):
                tiles.append((x, y))
        return tiles
    
    def screen_to_world(self, screen_x, screen_y):
        # normalized device coordinates
        x = (2 * screen_x) / self.app.window_width - 1
        y = (-2 * screen_y) / self.app.window_height + 1
        # reverse camera projection
        pjm = np.matrix(self.app.camera.projection_matrix)
        vm = np.matrix(self.app.camera.view_matrix)
        vp_inverse = (pjm * vm).getI()
        z = self.app.ui.active_art.layers_z[self.app.ui.active_art.active_layer]
        point = vp_inverse.dot(np.array([x, y, z, 0]))
        point = point.getA()
        cz = self.app.camera.z - z
        # apply camera offsets
        x = point[0][0] * cz + self.app.camera.x
        y = point[0][1] * cz + self.app.camera.y
        # TODO: does below properly account for distance between current
        # layer and camera? close but maybe still inaccurate
        y += self.app.camera.y_tilt
        return x, y, z
    
    def undo_preview_edits(self):
        for edit in self.preview_edits:
            edit.undo()
    
    def update_cursor_preview(self):
        # rebuild list of cursor preview commands
        if self.app.ui.selected_tool.show_preview:
            self.preview_edits = self.app.ui.selected_tool.get_paint_commands()
            for edit in self.preview_edits:
                edit.apply()
        else:
            self.preview_edits = []
    
    def start_paint(self):
        if self.app.ui.popup.visible or self.app.ui.console.visible:
            return
        # start a new command group, commit and clear any preview edits
        self.current_command = EditCommand(self.app.ui.active_art)
        self.current_command.add_command_tiles(self.preview_edits)
        self.preview_edits = []
        self.app.ui.active_art.set_unsaved_changes(True)
        #print(self.app.ui.active_art.command_stack)
    
    def finish_paint(self):
        "invoked by mouse button up and undo"
        if self.app.ui.popup.visible or self.app.ui.console.visible:
            return
        # push current command group onto undo stack
        if not self.current_command:
            return
        self.current_command.finish_time = self.app.elapsed_time
        self.app.ui.active_art.command_stack.commit_commands(self.current_command)
        self.current_command = None
        #print(self.app.ui.active_art.command_stack)
    
    def moved_this_frame(self):
        return self.moved or self.last_x != self.x or self.last_y != self.y
    
    def update(self, elapsed_time):
        # save old positions before update
        self.last_x, self.last_y = self.x, self.y
        # pulse alpha and scale
        self.alpha = 0.75 + (math.sin(elapsed_time / 100) / 2)
        #self.scale_x = 1.5 + (math.sin(elapsed_time / 100) / 50 - 0.5)
        mouse_moved = self.app.mouse_dx != 0 or self.app.mouse_dy != 0
        # update cursor from mouse if: mouse moved, camera moved w/o keyboard
        if mouse_moved or (not self.app.keyboard_editing and self.app.camera.moved_this_frame):
            # don't let mouse move cursor if text tool input is happening
            if not self.app.ui.text_tool.input_active:
                self.x, self.y, self.z = self.screen_to_world(self.app.mouse_x, self.app.mouse_y)
            self.moved = True
        if not self.moved and not self.app.ui.tool_settings_changed:
            return
        # snap to tile
        if not self.app.keyboard_editing:
            w, h = self.app.ui.active_art.quad_width, self.app.ui.active_art.quad_height
            char_aspect = w / h
            self.x = math.floor(self.x / w) * w
            self.y = math.ceil(self.y / h) * h * char_aspect
        # adjust for brush size
        if self.app.ui.selected_tool.brush_size:
            size = self.app.ui.selected_tool.brush_size
            self.scale_x = self.scale_y = size
            # don't reposition on resize if keyboard navigating
            if mouse_moved:
                size_offset = math.ceil(size / 2) - 1
                self.x -= size_offset
                self.y += size_offset
        else:
            self.scale_x = self.scale_y = 1
        self.undo_preview_edits()
        self.update_cursor_preview()
        if self.moved_this_frame():
            self.entered_new_tile()
    
    def end_update(self):
        "called at the end of App.update"
        self.moved = False
    
    def entered_new_tile(self):
        if self.current_command and self.app.ui.selected_tool.paint_while_dragging:
            # add new tile(s) to current command group
            self.current_command.add_command_tiles(self.preview_edits)
            self.app.ui.active_art.set_unsaved_changes(True)
            self.preview_edits = []
    
    def render(self):
        GL.glUseProgram(self.shader.program)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.app.camera.projection_matrix)
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.app.camera.view_matrix)
        GL.glUniform3f(self.position_uniform, self.x, self.y, self.z)
        GL.glUniform3f(self.scale_uniform, self.scale_x, self.scale_y, self.scale_z)
        GL.glUniform4fv(self.color_uniform, 1, self.color)
        GL.glUniform2f(self.quad_size_uniform, self.app.ui.active_art.quad_width, self.app.ui.active_art.quad_height)
        GL.glUniform1f(self.alpha_uniform, self.alpha)
        GL.glBindVertexArray(self.vao)
        # bind elem array instead of passing it to glDrawElements - latter
        # sends pyopengl a new array, which is deprecated and breaks on Mac.
        # thanks Erin Congden!
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        # draw 4 corners
        for i in range(4):
            tx,ty = corner_transforms[i][0], corner_transforms[i][1]
            ox,oy = corner_offsets[i][0], corner_offsets[i][1]
            GL.glUniform2f(self.xform_uniform, tx, ty)
            GL.glUniform2f(self.offset_uniform, ox, oy)
            GL.glDrawElements(GL.GL_TRIANGLES, self.vert_count,
                              GL.GL_UNSIGNED_INT, None)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
