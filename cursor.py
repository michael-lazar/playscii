import math, ctypes
import numpy as np
from OpenGL import GL

import vector
from edit_command import EditCommand
from renderable_sprite import UISpriteRenderable

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
    icon_scale_factor = 7 # 3.5 = 1:1
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
        if self.app.use_vao:
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
        if self.app.use_vao:
            GL.glBindVertexArray(0)
        # init tool sprite, tool will provide texture when rendered
        self.tool_sprite = UISpriteRenderable(self.app)
    
    def clamp_to_active_art(self):
        self.x = max(0, min(self.x, self.app.ui.active_art.width - 1))
        self.y = min(0, max(self.y, -self.app.ui.active_art.height + 1))
    
    def keyboard_move(self, delta_x, delta_y):
        if not self.app.ui.active_art:
            return
        self.x += delta_x
        self.y += delta_y
        self.clamp_to_active_art()
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
            return int(self.x), int(-self.y)
    
    def center_in_art(self):
        art = self.app.ui.active_art
        if not art:
            return
        self.x = round(art.width / 2) * art.quad_width
        self.y = round(-art.height / 2) * art.quad_height
        self.moved = True
    
    # !!TODO!! finish this, work in progress
    def get_tiles_under_drag(self):
        """
        returns list of tuple coordinates of all tiles under cursor's current
        position AND tiles it's moved over since last update
        """
        
        # TODO: get vector of last to current position, for each tile under
        # current brush, do line trace along grid towards last point
        
        # TODO: this works in two out of four diagonals,
        # swap current and last positions to determine delta?
        
        if self.last_x <= self.x:
            x0, y0 = self.last_x, -self.last_y
            x1, y1 = self.x, -self.y
        else:
            x0, y0 = self.x, -self.y
            x1, y1 = self.last_x, -self.last_y
        tiles = vector.get_tiles_along_line(x0, y0, x1, y1)
        print('drag from %s,%s to %s,%s:' % (x0, y0, x1, y1))
        print(tiles)
        return tiles
    
    def get_tiles_under_brush(self):
        """
        returns list of tuple coordinates of all tiles under the cursor @ its
        current brush size
        """
        size = self.app.ui.selected_tool.brush_size
        tiles = []
        x_start, y_start = int(self.x), int(-self.y)
        for y in range(y_start, y_start + size):
            for x in range(x_start, x_start + size):
                tiles.append((x, y))
        return tiles
    
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
        if self.app.ui.console.visible or self.app.ui.popup in self.app.ui.hovered_elements:
            return
        if self.app.ui.selected_tool is self.app.ui.grab_tool:
            self.app.ui.grab_tool.grab()
            return
        # start a new command group, commit and clear any preview edits
        self.current_command = EditCommand(self.app.ui.active_art)
        self.current_command.add_command_tiles(self.preview_edits)
        self.preview_edits = []
        self.app.ui.active_art.set_unsaved_changes(True)
        #print(self.app.ui.active_art.command_stack)
    
    def finish_paint(self):
        "invoked by mouse button up and undo"
        if self.app.ui.console.visible or self.app.ui.popup in self.app.ui.hovered_elements:
            return
        # push current command group onto undo stack
        if not self.current_command:
            return
        self.current_command.finish_time = self.app.get_elapsed_time()
        self.app.ui.active_art.command_stack.commit_commands([self.current_command])
        self.current_command = None
        # tools like rotate produce a different change each time, so update again
        if self.app.ui.selected_tool.update_preview_after_paint:
            self.update_cursor_preview()
        #print(self.app.ui.active_art.command_stack)
    
    def moved_this_frame(self):
        return self.moved or \
            int(self.last_x) != int(self.x) or \
            int(self.last_y) != int(self.y)
    
    def reposition_from_mouse(self):
        self.x, self.y, _ = vector.screen_to_world(self.app,
                                                   self.app.mouse_x,
                                                   self.app.mouse_y)
    
    def snap_to_tile(self):
        w, h = self.app.ui.active_art.quad_width, self.app.ui.active_art.quad_height
        char_aspect = w / h
        # round result for oddly proportioned charsets
        self.x = round(math.floor(self.x / w) * w)
        self.y = round(math.ceil(self.y / h) * h * char_aspect)
    
    def pre_first_update(self):
        # vector.screen_to_world result will be off because camera hasn't
        # moved yet, recalc view matrix
        self.app.camera.calc_view_matrix()
        self.reposition_from_mouse()
        self.snap_to_tile()
        self.update_cursor_preview()
        self.entered_new_tile()
    
    def update(self):
        # save old positions before update
        self.last_x, self.last_y = self.x, self.y
        # pulse alpha and scale
        self.alpha = 0.75 + (math.sin(self.app.get_elapsed_time() / 100) / 2)
        #self.scale_x = 1.5 + (math.sin(self.get_elapsed_time() / 100) / 50 - 0.5)
        mouse_moved = self.app.mouse_dx != 0 or self.app.mouse_dy != 0
        # update cursor from mouse if: mouse moved, camera moved w/o keyboard
        if mouse_moved or (not self.app.keyboard_editing and self.app.camera.moved_this_frame):
            # don't let mouse move cursor if text tool input is happening
            if not self.app.ui.text_tool.input_active:
                self.reposition_from_mouse()
                # cursor always at depth of active layer
                art = self.app.ui.active_art
                self.z = art.layers_z[art.active_layer] if art else 0
                self.moved = True
        if not self.moved and not self.app.ui.tool_settings_changed:
            return
        if not self.app.keyboard_editing and not self.app.ui.tool_settings_changed:
            self.snap_to_tile()
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
        # VAO vs non-VAO paths
        if self.app.use_vao:
            GL.glBindVertexArray(self.vao)
        else:
            attrib = self.shader.get_attrib_location # for brevity
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
            GL.glVertexAttribPointer(attrib('vertPosition'), 2, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                     ctypes.c_void_p(0))
            GL.glEnableVertexAttribArray(attrib('vertPosition'))
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
        if self.app.use_vao:
            GL.glBindVertexArray(0)
        GL.glUseProgram(0)
        # position and render tool icon
        ui = self.app.ui
        # special handling for quick grab
        if self.app.right_mouse:
            self.tool_sprite.texture = ui.grab_tool.get_icon_texture()
        else:
            self.tool_sprite.texture = ui.selected_tool.get_icon_texture()
        # scale same regardless of screen resolution
        aspect = self.app.window_height / self.app.window_width
        scale_x = self.tool_sprite.texture.width / self.app.window_width
        scale_x *= aspect * self.icon_scale_factor * self.app.ui.scale
        self.tool_sprite.scale_x = scale_x
        scale_y = self.tool_sprite.texture.height / self.app.window_height
        scale_y *= aspect * self.icon_scale_factor * self.app.ui.scale
        self.tool_sprite.scale_y = scale_y
        # top left of icon at bottom right of cursor
        size = ui.selected_tool.brush_size or 1
        x, y = self.x, self.y
        x += size * ui.active_art.quad_width
        # non-square charsets a bit tricky to properly account for
        char_aspect = ui.active_art.quad_height / ui.active_art.quad_width
        y -= (size / char_aspect) * ui.active_art.quad_height
        y *= char_aspect
        sx, sy = vector.world_to_screen_normalized(self.app, x, y, self.z)
        # screen-space offset by icon's height
        sy -= scale_y
        self.tool_sprite.x, self.tool_sprite.y = sx, sy
        self.tool_sprite.render()
