import os.path, time, platform
from OpenGL import GL
from OpenGL.GL import shaders

SHADER_PATH = 'shaders/'

class ShaderLord:
    
    # time in ms between checks for hot reload
    hot_reload_check_interval = 2 * 1000
    
    def __init__(self, app):
        "AWAKENS THE SHADERLORD"
        self.app = app
        self.shaders = []
    
    def new_shader(self, vert_source_file, frag_source_file):
        self.last_check = 0
        for shader in self.shaders:
            if shader.vert_source_file == vert_source_file and shader.frag_source_file == frag_source_file:
                #self.app.log('%s already uses same source' % shader)
                return shader
        s = Shader(self, vert_source_file, frag_source_file)
        self.shaders.append(s)
        return s
    
    def check_hot_reload(self):
        if self.app.get_elapsed_time() - self.last_check < self.hot_reload_check_interval:
            return
        self.last_check = self.app.get_elapsed_time()
        for shader in self.shaders:
            vert_shader_updated, frag_shader_updated = shader.has_updated()
            if vert_shader_updated:
                shader.recompile(GL.GL_VERTEX_SHADER)
            if frag_shader_updated:
                shader.recompile(GL.GL_FRAGMENT_SHADER)
    
    def destroy(self):
        for shader in self.shaders:
            shader.destroy()


class Shader:
    
    log_compile = False
    "If True, log shader compilation"
    # per-platform shader versions, declared here for easier CFG fiddling
    glsl_version_windows = 130
    glsl_version_unix = 130
    glsl_version_macos = 150
    glsl_version_es = 100
    
    def __init__(self, shader_lord, vert_source_file, frag_source_file):
        self.sl = shader_lord
        # vertex shader
        self.vert_source_file = vert_source_file
        self.last_vert_change = time.time()
        vert_source = self.get_shader_source(self.vert_source_file)
        if self.log_compile:
            self.sl.app.log('Compiling vertex shader %s...' % self.vert_source_file)
        self.vert_shader = self.try_compile_shader(vert_source, GL.GL_VERTEX_SHADER, self.vert_source_file)
        if self.log_compile and self.vert_shader:
            self.sl.app.log('Compiled vertex shader %s in %.6f seconds' % (self.vert_source_file, time.time() - self.last_vert_change))
        # fragment shader
        self.frag_source_file = frag_source_file
        self.last_frag_change = time.time()
        frag_source = self.get_shader_source(self.frag_source_file)
        if self.log_compile:
            self.sl.app.log('Compiling fragment shader %s...' % self.frag_source_file)
        self.frag_shader = self.try_compile_shader(frag_source, GL.GL_FRAGMENT_SHADER, self.frag_source_file)
        if self.log_compile and self.frag_shader:
            self.sl.app.log('Compiled fragment shader %s in %.6f seconds' % (self.frag_source_file, time.time() - self.last_frag_change))
        # shader program
        if self.vert_shader and self.frag_shader:
            self.program = shaders.compileProgram(self.vert_shader, self.frag_shader)
    
    def get_shader_source(self, source_file):
        src = open(SHADER_PATH + source_file, 'rb').read()
        # prepend shader version for different platforms
        if self.sl.app.context_es:
            shader_version = self.glsl_version_es
        elif platform.system() == 'Windows':
            shader_version = self.glsl_version_windows
        elif platform.system() == 'Darwin':
            shader_version = self.glsl_version_macos
        else:
            shader_version = self.glsl_version_unix
        version_string = '#version %s\n' % shader_version
        src = bytes(version_string, 'utf-8') + src
        return src
      
    def try_compile_shader(self, source, shader_type, source_filename):
        "Catch and print shader compilation exceptions"
        try:
            shader = shaders.compileShader(source, shader_type)
        except Exception as e:
            self.sl.app.log('%s: ' % source_filename)
            lines = e.args[0].split('\\n')
            # salvage block after "shader compile failure" enclosed in b""
            pre = lines.pop(0).split('b"')
            for line in pre + lines[:-1]:
                self.sl.app.log('  ' + line)
            return
        return shader
    
    def has_updated(self):
        vert_mod_time = os.path.getmtime(SHADER_PATH + self.vert_source_file)
        frag_mod_time = os.path.getmtime(SHADER_PATH + self.frag_source_file)
        # return two values: vert shader changed, frag shader changed
        vert_changed = vert_mod_time > self.last_vert_change
        frag_changed = frag_mod_time > self.last_frag_change
        # store new last modified time if changed
        if vert_changed:
            self.last_vert_change = time.time()
        if frag_changed:
            self.last_frag_change = time.time()
        return vert_changed, frag_changed
    
    def recompile(self, shader_type):
        file_to_reload = self.vert_source_file
        if shader_type == GL.GL_FRAGMENT_SHADER:
            file_to_reload = self.frag_source_file
        new_shader_source = self.get_shader_source(file_to_reload)
        try:
            new_shader = shaders.compileShader(new_shader_source, shader_type)
            # TODO: use try_compile_shader instead here, make sure exception passes thru ok
            self.sl.app.log('ShaderLord: success reloading %s' % file_to_reload)
        except:
            self.sl.app.log('ShaderLord: failed reloading %s' % file_to_reload)
            return
        # recompile program with new shader
        if shader_type == GL.GL_VERTEX_SHADER:
            self.vert_shader = new_shader
        else:
            self.frag_shader = new_shader
        self.program = shaders.compileProgram(self.vert_shader, self.frag_shader)
    
    def get_uniform_location(self, uniform_name):
        return GL.glGetUniformLocation(self.program, uniform_name)
    
    def get_attrib_location(self, attrib_name):
        return GL.glGetAttribLocation(self.program, attrib_name)
    
    def destroy(self):
        GL.glDeleteProgram(self.program)


class ShaderUniform:
    # MAYBE-TODO: class for remembering uniform name, type, index.
    # a Shader keeps a list of these, Renderables tell their Shader to set
    # them.  set methods use correct type and "try" to avoid crashes on
    # hot-reload when a uniform is commented out of live GLSL.
    # (try same for attributes?  more data)
    pass
