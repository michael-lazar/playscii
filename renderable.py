import math, ctypes
import numpy as np
from OpenGL import GL
from art import VERT_LENGTH
from palette import MAX_COLORS

# inactive layer alphas
LAYER_VIS_FULL = 1
LAYER_VIS_DIM = 0.25
LAYER_VIS_NONE = 0

class TileRenderable:
    
    # vertex shader: includes view projection matrix, XYZ camera uniforms
    vert_shader_source = 'renderable_v.glsl'
    # pixel shader: handles FG/BG colors
    frag_shader_source = 'renderable_f.glsl'
    log_create_destroy = False
    log_animation = False
    log_buffer_updates = False
    grain_strength = 0
    alpha = 1
    bg_alpha = 1
    move_rate = 1
    # when part of a GameObject, offset relative to origin
    # 0,0 = top left; 1,1 = bottom right; 0.5,0.5 = center
    origin_pct_x, origin_pct_y = 0.5, 0.5
    
    def __init__(self, app, art, game_object=None):
        self.app = app
        self.art = art
        self.art.renderables.append(self)
        # we may be attached to a game object
        self.game_object = game_object
        # set true momentarily by image export process
        self.exporting = False
        # flag for easy don't-render functionality
        self.visible = True
        # frame of our art's animation we're on
        self.frame = self.art.active_frame or 0
        self.animating = False
        self.anim_timer = 0
        # world space position and scale
        self.x, self.y, self.z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        # width and height in XY render space
        self.width, self.height = 1, 1
        self.reset_size()
        # TODO: object rotation matrix, if needed
        self.goal_x, self.goal_y, self.goal_z = 0, 0, 0
        self.moving = False
        self.camera = self.app.camera
        # bind VAO etc before doing shaders etc
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.charset_width_uniform = self.shader.get_uniform_location('charMapWidth')
        self.charset_height_uniform = self.shader.get_uniform_location('charMapHeight')
        self.char_uv_width_uniform = self.shader.get_uniform_location('charUVWidth')
        self.char_uv_height_uniform = self.shader.get_uniform_location('charUVHeight')
        self.charset_tex_uniform = self.shader.get_uniform_location('charset')
        self.palette_tex_uniform = self.shader.get_uniform_location('palette')
        self.grain_tex_uniform = self.shader.get_uniform_location('grain')
        self.palette_width_uniform = self.shader.get_uniform_location('palTextureWidth')
        self.grain_strength_uniform = self.shader.get_uniform_location('grainStrength')
        self.alpha_uniform = self.shader.get_uniform_location('alpha')
        self.bg_alpha_uniform = self.shader.get_uniform_location('bgColorAlpha')
        self.create_buffers()
        # finish
        GL.glBindVertexArray(0)
        if self.log_create_destroy:
            self.app.log('created: %s' % self)
    
    def __str__(self):
        "for debug purposes, return a concise unique name"
        for i,r in enumerate(self.art.renderables):
            if r is self:
                break
        return '%s %s %s' % (self.art.filename, self.__class__.__name__, i)
    
    def create_buffers(self):
        # vertex positions and elements
        # determine vertex count needed for render
        self.vert_count = int(len(self.art.elem_array))
        self.vert_buffer, self.elem_buffer = GL.glGenBuffers(2)
        self.update_buffer(self.vert_buffer, self.art.vert_array,
                           GL.GL_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_FLOAT, 'vertPosition', VERT_LENGTH)
        self.update_buffer(self.elem_buffer, self.art.elem_array,
                           GL.GL_ELEMENT_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_UNSIGNED_INT, None, None)
        # tile data buffers
        # use GL_DYNAMIC_DRAW given they change every time a char/color changes
        self.char_buffer, self.uv_buffer = GL.glGenBuffers(2)
        # character indices (which become vertex UVs)
        self.update_buffer(self.char_buffer, self.art.chars[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'charIndex', 1)
        # UV "mods" - modify UV derived from character index
        self.update_buffer(self.uv_buffer, self.art.uv_mods[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'uvMod', 2)
        self.fg_buffer, self.bg_buffer = GL.glGenBuffers(2)
        # foreground/background color indices (which become rgba colors)
        self.update_buffer(self.fg_buffer, self.art.fg_colors[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'fgColorIndex', 1)
        self.update_buffer(self.bg_buffer, self.art.bg_colors[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'bgColorIndex', 1)
    
    def update_geo_buffers(self):
        self.update_buffer(self.vert_buffer, self.art.vert_array, GL.GL_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_FLOAT, None, None)
        self.update_buffer(self.elem_buffer, self.art.elem_array, GL.GL_ELEMENT_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_UNSIGNED_INT, None, None)
        # total vertex count probably changed
        self.vert_count = int(len(self.art.elem_array))
    
    def update_tile_buffers(self, update_chars, update_uvs, update_fg, update_bg):
        updates = {}
        if update_chars:
            updates[self.char_buffer] = self.art.chars
        if update_uvs:
            updates[self.uv_buffer] = self.art.uv_mods
        if update_fg:
            updates[self.fg_buffer] = self.art.fg_colors
        if update_bg:
            updates[self.bg_buffer] = self.art.bg_colors
        for update in updates:
            self.update_buffer(update, updates[update][self.frame],
                               GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW,
                               GL.GL_FLOAT, None, None)
    
    def update_buffer(self, buffer_index, array, target, buffer_type, data_type,
                      attrib_name, attrib_size):
        if self.log_buffer_updates:
            self.app.log('update_buffer: %s, %s, %s, %s, %s, %s, %s' % (buffer_index, array, target, buffer_type, data_type, attrib_name, attrib_size))
        GL.glBindBuffer(target, buffer_index)
        GL.glBufferData(target, array.nbytes, array, buffer_type)
        if attrib_name:
            attrib = self.shader.get_attrib_location(attrib_name)
            GL.glEnableVertexAttribArray(attrib)
            GL.glVertexAttribPointer(attrib, attrib_size, data_type,
                                     GL.GL_FALSE, 0, ctypes.c_void_p(0))
        # unbind each buffer before binding next
        GL.glBindBuffer(target, 0)
    
    def advance_frame(self):
        self.set_frame(self.frame + 1)
    
    def rewind_frame(self):
        self.set_frame(self.frame - 1)
    
    def set_frame(self, new_frame_index):
        old_frame = self.frame
        self.frame = new_frame_index % self.art.frames
        self.update_tile_buffers(True, True, True, True)
        if self.log_animation:
            self.app.log('%s animating from frames %s to %s' % (self, old_frame, self.frame))
    
    def start_animating(self):
        self.animating = True
        self.anim_timer = 0
    
    def stop_animating(self):
        self.animating = False
        # restore to active frame if stopping
        if not self.app.game_mode:
            self.set_frame(self.art.active_frame)
    
    def set_art(self, new_art):
        if self.art:
            self.art.renderables.remove(self)
        self.art = new_art
        self.reset_size()
        self.art.renderables.append(self)
        # make sure frame is valid
        self.frame %= self.art.frames
        #self.create_buffers()
        self.update_geo_buffers()
        self.update_tile_buffers(True, True, True, True)
        #print('%s now uses Art %s' % (self, self.art.filename))
    
    def reset_size(self):
        self.width = self.art.width * self.art.quad_width * abs(self.scale_x)
        self.height = self.art.height * self.art.quad_height * self.scale_y
    
    def move_to(self, x, y, z, travel_time=None):
        # for fixed travel time, set move rate accordingly
        if travel_time:
            frames = (travel_time * 1000) / self.app.frame_time
            dx = x - self.x
            dy = y - self.y
            dz = z - self.z
            dist = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
            self.move_rate = dist / frames
        self.moving = True
        self.goal_x, self.goal_y, self.goal_z = x, y, z
        if self.log_animation:
            self.app.log('%s will move to %s,%s' % (self.art.filename, self.goal_x, self.goal_y))
    
    def update_transform_from_object(self, obj):
        "updates our position & scale based on that of given game object"
        self.z = obj.z
        if self.scale_x != obj.scale_x or self.scale_y != obj.scale_y:
            self.reset_size()
        if obj.flip_x:
            self.x = obj.x + (self.width * self.origin_pct_x)
        else:
            self.x = obj.x - (self.width * self.origin_pct_x)
        self.y = obj.y + (self.height * self.origin_pct_y)
        self.scale_x, self.scale_y = obj.scale_x, obj.scale_y
        if obj.flip_x:
            self.scale_x *= -1
        self.scale_z = obj.scale_z
    
    def update_loc(self):
        # TODO: probably time to bust out the ol' vector module for this stuff
        # get delta
        dx = self.goal_x - self.x
        dy = self.goal_y - self.y
        dz = self.goal_z - self.z
        dist = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        # close enough?
        if dist <= self.move_rate:
            self.x = self.goal_x
            self.y = self.goal_y
            self.z = self.goal_z
            self.moving = False
            return
        # normalize
        inv_dist = 1 / dist
        dir_x = dx * inv_dist
        dir_y = dy * inv_dist
        dir_z = dz * inv_dist
        self.x += self.move_rate * dir_x
        self.y += self.move_rate * dir_y
        self.z += self.move_rate * dir_z
        #self.app.log('%s moved to %s,%s' % (self, self.x, self.y))
    
    def update(self):
        if self.game_object:
            self.update_transform_from_object(self.game_object)
        elif self.moving:
            self.update_loc()
        if not self.animating:
            return
        self.anim_timer += self.app.delta_time / 1000
        this_frame_delay = self.art.frame_delays[self.frame]
        while self.anim_timer > this_frame_delay:
            self.anim_timer -= this_frame_delay
            # iterate through frames, but don't call set_frame until the end
            self.frame = (self.frame + 1) % self.art.frames
            this_frame_delay = self.art.frame_delays[self.frame]
        self.set_frame(self.frame)
    
    def destroy(self):
        GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(6, [self.vert_buffer, self.elem_buffer, self.char_buffer, self.uv_buffer, self.fg_buffer, self.bg_buffer])
        if self.log_create_destroy:
            self.app.log('destroyed: %s' % self)
    
    def get_projection_matrix(self):
        """
        UIRenderable overrides this so it doesn't have to override
        Renderable.render and duplicate lots of code.
        """
        return np.eye(4, 4) if self.exporting else self.camera.projection_matrix
    
    def get_view_matrix(self):
        return np.eye(4, 4) if self.exporting else self.camera.view_matrix
    
    def get_loc(self):
        export_loc = (-1, 1, 0)
        return export_loc if self.exporting else (self.x, self.y, self.z)
    
    def get_scale(self):
        if not self.exporting:
            return (self.scale_x, self.scale_y, self.scale_z)
        x = 2 / (self.art.width * self.art.quad_width)
        y = 2 / (self.art.height * self.art.quad_height)
        return (x, y, 1)
    
    def render_for_export(self):
        self.exporting = True
        # cursor might be hovering, undo any preview changes
        for edit in self.art.app.cursor.preview_edits:
            edit.undo()
        # update art to commit changes to the renderable
        self.art.update()
        self.render(0)
        self.exporting = False
    
    def render(self, layers=None, z_override=None):
        if not self.visible:
            return
        GL.glUseProgram(self.shader.program)
        # bind textures - character set, palette, UI grain
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glUniform1i(self.charset_tex_uniform, 0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.art.charset.texture.gltex)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glUniform1i(self.palette_tex_uniform, 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.art.palette.texture.gltex)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glUniform1i(self.grain_tex_uniform, 2)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.app.ui.grain_texture.gltex)
        # set active texture unit back after binding 2nd-Nth textures
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glUniform1i(self.charset_width_uniform, self.art.charset.map_width)
        GL.glUniform1i(self.charset_height_uniform, self.art.charset.map_height)
        GL.glUniform1f(self.char_uv_width_uniform, self.art.charset.u_width)
        GL.glUniform1f(self.char_uv_height_uniform, self.art.charset.v_height)
        GL.glUniform1f(self.palette_width_uniform, MAX_COLORS)
        GL.glUniform1f(self.grain_strength_uniform, self.grain_strength)
        # camera uniforms
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE,
                              self.get_projection_matrix())
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE,
                              self.get_view_matrix())
        # TODO renderer opti: all the above are probably true of all
        # game mode renderables!
        # ie you could set those then render all VAOs changing only the below
        # uniforms
        GL.glUniform1f(self.bg_alpha_uniform, self.bg_alpha)
        GL.glUniform3f(self.scale_uniform, *self.get_scale())
        GL.glBindVertexArray(self.vao)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        # draw all specified layers if no list given
        if layers is None:
            # sort layers in Z depth
            layers = list(range(self.art.layers))
            layers.sort(key=lambda i: self.art.layers_z[i], reverse=False)
        # handle a single int param
        elif type(layers) is int:
            layers = [layers]
        layer_size = int(len(self.art.elem_array) / self.art.layers)
        for i in layers:
            layer_start = i * layer_size
            layer_end = layer_start + layer_size
            # for active art, dim all but active layer based on UI setting
            if not self.app.game_mode and self.art is self.app.ui.active_art and i != self.art.active_layer:
                GL.glUniform1f(self.alpha_uniform, self.alpha * self.app.inactive_layer_visibility)
            else:
                GL.glUniform1f(self.alpha_uniform, self.alpha)
            # use position offset instead of baked-in Z for layers - this
            # way a layer's Z can change w/o rebuilding its vert array
            x, y, z = self.get_loc()
            z += self.art.layers_z[i]
            z = z_override if z_override else z
            GL.glUniform3f(self.position_uniform, x, y, z)
            GL.glDrawElements(GL.GL_TRIANGLES, layer_size, GL.GL_UNSIGNED_INT,
                ctypes.c_void_p(layer_start * ctypes.sizeof(ctypes.c_uint)))
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)


class OnionTileRenderable(TileRenderable):
    
    # never animate
    def start_animating(self):
        pass
    
    def stop_animating(self):
        pass
