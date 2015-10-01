import os, math

from art import Art
from renderable import TileRenderable
from renderable_line import OriginIndicatorRenderable, BoundsIndicatorRenderable

from collision import Collideable, CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

# facings
GOF_LEFT = 0
GOF_RIGHT = 1
GOF_FRONT = 2
GOF_BACK = 3

FACINGS = {
    GOF_LEFT: 'left',
    GOF_RIGHT: 'right',
    GOF_FRONT: 'front',
    GOF_BACK: 'back'
}

FACING_DIRS = {
    GOF_LEFT: (-1, 0),
    GOF_RIGHT: (1, 0),
    GOF_FRONT: (0, -1),
    GOF_BACK: (0, 1)
}

DEFAULT_STATE = 'stand'

class GameObjectRenderable(TileRenderable):
    
    def get_loc(self):
        x, y, z = self.x, self.y, self.z
        if self.game_object:
            off_x, off_y, off_z = self.game_object.get_render_offset()
            x += off_x
            y += off_y
            z += off_z
        return x, y, z


class GameObject:
    
    # if specified, this art will be loaded from disk and used as object's
    # default appearance. if object has states/facings, this is the "base"
    # filename prefix, eg "hero" in "hero_stand_front.psci"
    art_src = 'game_object_default'
    # if true, art will change with current state; depends on file naming
    state_changes_art = False
    # if true, object will go to stand state any time velocity is zero
    stand_if_not_moving = False
    # list of valid states for this object, used to find anims
    valid_states = [DEFAULT_STATE]
    # if true, art will change with facing AND state
    facing_changes_art = False
    # if generate_art is True, blank art will be created with these
    # dimensions, charset, and palette
    generate_art = False
    # if True, object's art will animate on init/reset
    animating = False
    art_width, art_height = 8, 8
    art_charset, art_palette = None, None
    # Y-sort: if true, object will sort according to its Y position
    y_sort = False
    # if False, don't do move physics updates for this object
    physics_move = True
    # acceleration per update from player movement
    move_accel_x = move_accel_y = 200.
    ground_friction = 10.0
    air_friction = 25.0
    # mass: negative number = infinitely dense
    mass = 1.
    # bounciness aka restitution, % of velocity reflected on bounce
    bounciness = 0.25
    # near-zero point at which velocity is set to zero
    stop_velocity = 0.1
    log_move = False
    log_load = False
    log_spawn = False
    visible = True
    alpha = 1.
    # location is protected from edit mode drags, can't click to select
    locked = False
    show_origin = False
    show_bounds = False
    show_collision = False
    # collision shape (tile, circle, AABB) and type (channel)
    collision_shape_type = CST_NONE
    collision_type = CT_NONE
    # segment thickness for AABB / tile based collision
    seg_thickness = 0.1
    # collision layer name for CST_TILE objects
    col_layer_name = 'collision'
    # collision circle/box offset from origin
    col_offset_x, col_offset_y = 0., 0.
    col_radius = 1.
    # AABB top left / bottom right coordinates
    col_box_left_x, col_box_right_x = -1, 1
    col_box_top_y, col_box_bottom_y = -1, 1
    # art offset from pivot: renderable's origin_pct set to this if !None
    # 0,0 = top left; 1,1 = bottom right; 0.5,0.5 = center
    art_off_pct_x, art_off_pct_y = 0.5, 0.5
    # if True, write this object to save files
    should_save = True
    # list of members to serialize (no weak refs!)
    serialized = ['name', 'x', 'y', 'z', 'art_src', 'visible', 'locked', 'y_sort',
                  'art_off_pct_x', 'art_off_pct_y', 'alpha', 'state', 'facing',
                  'animating', 'scale_x', 'scale_y']
    # members that don't need to be serialized, but should be exposed to
    # object edit UI
    editable = ['show_collision', 'mass', 'bounciness', 'stop_velocity']
    # if setting a given property should run some logic, specify method here
    set_methods = {'art_src': 'set_art_src', 'alpha': 'set_alpha',
                   'scale_x': 'set_scale_x', 'scale_y': 'set_scale_y',
                   'name': 'rename'
    }
    # can select in edit mode
    selectable = True
    # can delete in edit mode
    deleteable = True
    # do not list in edit mode UI - system use only!
    do_not_list = False
    # objects to spawn as attachments: key is member name, value is class
    attachment_classes = {}
    # class blacklist for collisions - string names of classes, not class defs
    noncolliding_classes = []
    # dict of sound filenames, keys are string "tags"
    sound_filenames = {}
    # looping sounds that should play while in a given state
    looping_state_sounds = {}
    
    def __init__(self, world, obj_data=None):
        self.x, self.y, self.z = 0., 0., 0.
        self.scale_x, self.scale_y, self.scale_z = 1., 1., 1.
        # dict of rooms we're in - if empty, object appears in all rooms
        self.rooms = {}
        # every object gets a state and facing, even if it never changes
        self.state = DEFAULT_STATE
        self.facing = GOF_FRONT
        self.name = self.get_unique_name()
        # apply serialized data before most of init happens
        # properties that need non-None defaults should be declared above
        if obj_data:
            for v in self.serialized:
                if not v in obj_data:
                    if self.log_load:
                        self.app.dev_log("Serialized property '%s' not found for %s" % (v, self.name))
                    continue
                # if value is in data and serialized list but undeclared, do so
                if not hasattr(self, v):
                    setattr(self, v, None)
                # match type of variable as declared, eg loc might be written as
                # an int in the JSON so preserve its floatness
                if getattr(self, v) is not None:
                    src_type = type(getattr(self, v))
                    setattr(self, v, src_type(obj_data[v]))
                else:
                    setattr(self, v, obj_data[v])
        self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
        # user-intended acceleration
        self.move_x, self.move_y = 0, 0
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        self.flip_x = False
        self.world = world
        self.app = self.world.app
        # load/create assets
        self.arts = {}
        # if art_src not specified, create a new art according to dimensions
        if self.generate_art:
            self.art_src = '%s_art' % self.name
            self.art = self.app.new_art(self.art_src, self.art_width,
                                        self.art_height, self.art_charset,
                                        self.art_palette)
        else:
            self.load_arts()
        if self.art is None or not self.art.valid:
            # grab first available art
            if len(self.arts) > 0:
                for art in self.arts:
                    self.art = self.arts[art]
                    break
        if not self.art:
            self.app.log("Couldn't spawn GameObject with art %s" % self.art_src)
            return
        self.renderable = GameObjectRenderable(self.app, self.art, self)
        self.renderable.alpha = self.alpha
        self.origin_renderable = OriginIndicatorRenderable(self.app, self)
        # 1px LineRenderable showing object's bounding box
        self.bounds_renderable = BoundsIndicatorRenderable(self.app, self)
        for art in self.arts.values():
            if not art in self.world.art_loaded:
                self.world.art_loaded.append(art)
        # remember previous collision type for enable/disable
        self.orig_collision_type = None
        self.collision = Collideable(self)
        self.world.new_objects[self.name] = self
        self.attachments = []
        if self.attachment_classes:
            for atch_name,atch_class_name in self.attachment_classes.items():
                atch_class = self.world.classes[atch_class_name]
                attachment = atch_class(self.world)
                self.attachments.append(attachment)
                attachment.attach_to(self)
                setattr(self, atch_name, attachment)
        self.should_destroy = False
        # flag that tells us we should run post_init next update
        self.pre_first_update_run = False
        self.last_state = None
        if self.animating and self.art.frames > 0:
            self.start_animating()
        if self.log_spawn:
            self.app.log('Spawned %s with Art %s' % (self.name, os.path.basename(self.art.filename)))
    
    def get_unique_name(self):
        # generate somewhat human-readable unique name for object
        name = str(self)
        return '%s_%s' % (type(self).__name__, name[name.rfind('x')+1:-1])
    
    def rename(self, new_name):
        "gives this object a new name. doesn't accept already-in-use names"
        for obj in self.world.objects.values():
            if not obj is self and obj.name == new_name:
                return
        old_name = self.name
        self.name = new_name
        for room in self.world.rooms.values():
            if self in room.objects.values():
                room.objects.pop(old_name)
                room.objects[self.name] = self
    
    def pre_first_update(self):
        """
        runs before first update; use this for any logic that depends on
        init/creation being done ie all objects being present
        """
        pass
    
    def load_arts(self):
        "fill self.arts dict with art assets: states, facings"
        self.art = self.app.load_art(self.art_src, False)
        # if no states, use a single art always
        if not self.state_changes_art:
            self.arts[self.art_src] = self.art
            return
        for state in self.valid_states:
            if self.facing_changes_art:
                # load each facing for each state
                for facing in FACINGS.values():
                    art_name = '%s_%s_%s' % (self.art_src, state, facing)
                    art = self.app.load_art(art_name, False)
                    if art:
                        self.arts[art_name] = art
            else:
                # load each state
                art_name = '%s_%s' % (self.art_src, state)
                art = self.app.load_art(art_name, False)
                if art:
                    self.arts[art_name] = art
        # get reasonable default pose
        self.art, self.flip_x = self.get_art_for_state()
    
    def is_point_inside(self, x, y):
        "returns True if given point is inside our bounds"
        left, top, right, bottom = self.get_edges()
        return left <= x <= right and bottom <= y <= top
    
    def get_edges(self):
        "returns coords of our bounds (left, top, right, bottom)"
        left = self.x - (self.renderable.width * self.art_off_pct_x)
        right = self.x + (self.renderable.width * self.art_off_pct_x)
        bottom = self.y - (self.renderable.height * self.art_off_pct_y)
        top = self.y + (self.renderable.height * self.art_off_pct_y)
        return left, top, right, bottom
    
    def distance_to_object(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx ** 2 + dy ** 2)
    
    def normal_to_object(self, other):
        "returns tuple normal pointing in direction of given object"
        dist = self.distance_to_object(other)
        dx, dy = other.x - self.x, other.y - self.y
        if dist == 0:
            return 0, 0
        inv_dist = 1 / dist
        return dx * inv_dist, dy * inv_dist
    
    def get_render_offset(self):
        # allow subclasses to provide offsets based on stuff, eg "fake Z"
        return 0, 0, 0
    
    def is_dynamic(self):
        return self.physics_move and self.collision_type in CTG_DYNAMIC
    
    def start_dragging(self):
        self.disable_collision()
    
    def stop_dragging(self):
        if self.world.object_grid_snap:
            self.x = round(self.x)
            self.y = round(self.y)
            # if odd width/height, origin will be between quads and
            # edges will be off-grid; nudge so that edges are on-grid
            if self.art.width % 2 != 0:
                self.x += self.art.quad_width / 2
            if self.art.height % 2 != 0:
                self.y += self.art.quad_height / 2
        self.enable_collision()
        if self.collision_shape_type == CST_TILE:
            self.collision.create_shapes()
    
    def is_entering_state(self, state):
        return self.state == state and self.last_state != state
    
    def is_exiting_state(self, state):
        return self.state != state and self.last_state == state
    
    def play_sound(self, sound_name, loops=0, allow_multiple=False):
        # use sound_name as filename if it's not in our filenames dict
        sound_filename = self.sound_filenames.get(sound_name, sound_name)
        sound_filename = self.world.sounds_dir + sound_filename
        self.world.app.al.object_play_sound(self, sound_filename,
                                            loops, allow_multiple)
    
    def stop_sound(self, sound_name):
        sound_filename = self.sound_filenames.get(sound_name, sound_name)
        sound_filename = self.world.sounds_dir + sound_filename
        self.world.app.al.object_stop_sound(self, sound_filename)
    
    def stop_all_sounds(self):
        self.world.app.al.object_stop_all_sounds(self)
    
    def enable_collision(self):
        self.collision_type = self.orig_collision_type
    
    def disable_collision(self):
        if self.collision_type == CT_NONE:
            return
        # remember prior collision type
        self.orig_collision_type = self.collision_type
        self.collision_type = CT_NONE
    
    def started_colliding(self, other):
        pass
    
    def stopped_colliding(self, other):
        # called from check_finished_contacts
        self.collision.contacts.pop(other.name)
    
    def check_finished_contacts(self):
        """
        updates our collideable's contacts table for contacts that were
        happening last update but not this one, and call stopped_colliding
        """
        # put stopped-colliding objects in a list to process after checks
        finished = []
        # keep separate list of names of objects no longer present
        destroyed = []
        for obj_name,contact in self.collision.contacts.items():
            if contact[2] < self.world.cl.ticks:
                # object might have been destroyed
                obj = self.world.objects.get(obj_name, None)
                if obj:
                    finished.append(obj)
                else:
                    destroyed.append(obj_name)
        for obj_name in destroyed:
            self.collision.contacts.pop(obj_name)
        for obj in finished:
            self.stopped_colliding(obj)
            obj.stopped_colliding(self)
    
    def get_contacting_objects(self):
        return [self.world.objects[obj] for obj in self.collision.contacts]
    
    def is_overlapping(self, other):
        "return True if we overlap with other object's collision"
        return other.name in self.collision.contacts
    
    def are_bounds_overlapping(self, other):
        "return True if we overlap with other object's art bounds"
        left, top, right, bottom = self.get_edges()
        corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
        for x,y in corners:
            if other.is_point_inside(x, y):
                return True
        return False
    
    def overlapped(self, other, dx, dy):
        started = not other.name not in self.collision.contacts
        # create or update contact info: (depth_x, depth_y, timestamp)
        # TODO: maybe use a named tuple here
        self.collision.contacts[other.name] = (dx, dy, self.world.cl.ticks)
        if started:
            self.started_colliding(other)
        # return False if we shouldn't collide with this class
        for ncc_name in self.noncolliding_classes:
            ncc = self.world.classes[ncc_name]
            if isinstance(other, ncc):
                return False
        return True
    
    def get_all_art(self):
        "returns a list of all Art used by this object"
        return list(self.arts.keys())
    
    def start_animating(self):
        self.renderable.start_animating()
    
    def stop_animating(self):
        self.renderable.stop_animating()
    
    def set_object_property(self, prop_name, new_value):
        if not hasattr(self, prop_name):
            return
        if prop_name in self.set_methods:
            method = getattr(self, self.set_methods[prop_name])
            method(new_value)
        else:
            setattr(self, prop_name, new_value)
    
    def get_art_for_state(self, state=None):
        "returns art (and 'flip X' bool) that best represents current state"
        # use current state if none specified
        state = self.state if state is None else state
        art_state_name = '%s_%s' % (self.art_src, self.state)
        # simple case: no facing, just state
        if not self.facing_changes_art:
            # return art for current state, use default if not available
            if art_state_name in self.arts:
                return self.arts[art_state_name], False
            else:
                default_name = '%s_%s' % (self.art_src, self.state or DEFAULT_STATE)
                assert(default_name in self.arts)
                return self.arts[default_name], False
        # more complex case: art determined by both state and facing
        facing_suffix = FACINGS[self.facing]
        # first see if anim exists for this exact state, skip subsequent logic
        exact_name = '%s_%s' % (art_state_name, facing_suffix)
        if exact_name in self.arts:
            return self.arts[exact_name], False
        # see what anims are available and try to choose best for facing
        has_state = False
        for anim in self.arts:
            if anim.startswith(art_state_name):
                has_state = True
                break
        # if NO anims for current state, fall back to default
        if not has_state:
            default_name = '%s_%s' % (self.art_src, DEFAULT_STATE)
            art_state_name = default_name
        front_name = '%s_%s' % (art_state_name, FACINGS[GOF_FRONT])
        left_name = '%s_%s' % (art_state_name, FACINGS[GOF_LEFT])
        right_name = '%s_%s' % (art_state_name, FACINGS[GOF_RIGHT])
        back_name = '%s_%s' % (art_state_name, FACINGS[GOF_BACK])
        has_front = front_name in self.arts
        has_left = left_name in self.arts
        has_right = right_name in self.arts
        has_sides = has_left or has_right
        # throw an error if nothing basic is available
        assert(has_front or has_sides)
        # if left/right opposite available, flip it
        if self.facing == GOF_LEFT and has_right:
            return self.arts[right_name], True
        elif self.facing == GOF_RIGHT and has_left:
            return self.arts[left_name], True
        # if left or right but neither, use front
        elif self.facing in [GOF_LEFT, GOF_RIGHT] and not has_sides:
            return self.arts[front_name], False
        # if no front but sides, use either
        elif self.facing == GOF_FRONT and has_sides:
            if has_right:
                return self.arts[right_name], False
            elif has_left:
                return self.arts[left_name], False
        # if no back, use sides or, as last resort, front
        elif self.facing == GOF_BACK and has_sides:
            if has_right:
                return self.arts[right_name], False
            elif has_left:
                return self.arts[left_name], False
            else:
                return self.arts[front_name], False
        # fall-through: keep using current art
        return self.art, False
    
    def set_art(self, new_art, start_animating=True):
        if new_art is self.art:
            return
        self.art = new_art
        self.renderable.set_art(self.art)
        self.bounds_renderable.set_art(self.art)
        if self.collision_shape_type == CST_TILE:
            self.collision.create_shapes()
        if (start_animating or self.animating) and new_art.frames > 1:
            self.renderable.start_animating()
    
    def set_art_src(self, new_art_filename):
        if self.art_src == new_art_filename:
            return
        new_art = self.app.load_art(new_art_filename)
        if not new_art:
            return
        self.art_src = new_art_filename
        # reset arts dict
        self.arts = {}
        self.load_arts()
        self.set_art(new_art)
    
    def set_loc(self, x, y, z=None):
        self.x, self.y = x, y
        self.z = z or 0
    
    def set_scale(self, x, y, z):
        self.scale_x, self.scale_y, self.scale_z = x, y, z
        self.renderable.scale_x = self.scale_x
        self.renderable.scale_y = self.scale_y
        self.renderable.reset_size()
    
    def set_scale_x(self, new_x):
        self.set_scale(new_x, self.scale_y, self.scale_z)
    
    def set_scale_y(self, new_y):
        self.set_scale(self.scale_x, new_y, self.scale_z)
    
    def set_alpha(self, new_alpha):
        self.renderable.alpha = self.alpha = new_alpha
    
    def allow_move(self, dx, dy):
        "return True only if this object is allowed to move based on input"
        return True
    
    def move(self, dir_x, dir_y):
        "handle player-initiated velocity"
        # don't handle moves while game paused
        # (add override flag if this becomes necessary)
        if self.world.paused:
            return
        # check allow_move first
        if not self.allow_move(dir_x, dir_y):
            return
        self.move_x += dir_x
        self.move_y += dir_y
    
    def is_on_ground(self):
        "logic for determining if object is on ground vs not"
        return True
    
    def get_friction(self):
        return self.ground_friction if self.is_on_ground() else self.air_friction
    
    def is_affected_by_gravity(self):
        return False
    
    def get_gravity(self):
        return self.world.gravity_x, self.world.gravity_y, self.world.gravity_z
    
    def cut_xyz(self, x, y, z, threshold):
        x = x if abs(x) > threshold else 0
        y = y if abs(y) > threshold else 0
        z = z if abs(z) > threshold else 0
        return x, y, z
    
    def get_acceleration(self, vel_x, vel_y, vel_z):
        force_x = self.move_x * self.move_accel_x
        force_y = self.move_y * self.move_accel_y
        force_z = 0
        if self.is_affected_by_gravity():
            grav_x, grav_y, grav_z = self.get_gravity()
            force_x += grav_x * self.mass
            force_y += grav_y * self.mass
            force_z += grav_z * self.mass
        # friction / drag
        friction = self.get_friction()
        speed = math.sqrt(vel_x ** 2 + vel_y ** 2 + vel_z ** 2)
        force_x -= friction * self.mass * vel_x
        force_y -= friction * self.mass * vel_y
        force_z -= friction * self.mass * vel_z
        # divide force by mass to get acceleration
        accel_x = force_x / self.mass
        accel_y = force_y / self.mass
        accel_z = force_z / self.mass
        # zero out acceleration beneath a threshold
        # TODO: determine if this should be made tunable
        return self.cut_xyz(accel_x, accel_y, accel_z, 0.01)
    
    def apply_move(self):
        # verlet integration w/ half-step velocity
        accel_x, accel_y, accel_z = self.get_acceleration(self.vel_x, self.vel_y, self.vel_z)
        timestep = self.world.app.timestep / 1000
        hsvel_x = self.vel_x + 0.5 * timestep * accel_x
        hsvel_y = self.vel_y + 0.5 * timestep * accel_y
        hsvel_z = self.vel_z + 0.5 * timestep * accel_z
        self.x += hsvel_x * timestep
        self.y += hsvel_y * timestep
        self.z += hsvel_z * timestep
        accel_x, accel_y, accel_z = self.get_acceleration(hsvel_x, hsvel_y, hsvel_z)
        self.vel_x = hsvel_x + 0.5 * timestep * accel_x
        self.vel_y = hsvel_y + 0.5 * timestep * accel_y
        self.vel_z = hsvel_z + 0.5 * timestep * accel_z
        self.vel_x, self.vel_y, self.vel_z = self.cut_xyz(self.vel_x, self.vel_y, self.vel_z, self.stop_velocity)
    
    def moved_this_frame(self):
        delta = math.sqrt(abs(self.last_x - self.x) ** 2 + abs(self.last_y - self.y) ** 2 + abs(self.last_z - self.z) ** 2)
        return delta > self.stop_velocity
    
    def update_state(self):
        "update state based on things like movement"
        if self.stand_if_not_moving and not self.moved_this_frame():
            self.state = DEFAULT_STATE
    
    def update_facing(self):
        dx, dy = self.x - self.last_x, self.y - self.last_y
        if dx == 0 and dy == 0:
            return
        # TODO: flag for "side view only" objects
        if abs(dy) > abs(dx):
            self.facing = GOF_BACK if dy >= 0 else GOF_FRONT
        else:
            self.facing = GOF_RIGHT if dx >= 0 else GOF_LEFT
    
    def update_state_sounds(self):
        "play looping sounds associated with any states"
        for state,sound in self.looping_state_sounds.items():
            if self.is_entering_state(state):
                self.play_sound(sound, loops=-1)
            elif self.is_exiting_state(state):
                self.stop_sound(sound)
    
    def frame_begin(self):
        self.move_x, self.move_y = 0, 0
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        # if we're just entering stand state, play any sound for it
        if self.last_state is None:
            self.update_state_sounds()
        self.last_state = self.state
    
    def frame_update(self):
        if not self.art.updated_this_tick:
            self.art.update()
        # update art based on state (and possibly facing too)
        if self.state_changes_art:
            new_art, flip_x = self.get_art_for_state()
            self.set_art(new_art)
            self.flip_x = flip_x
    
    def pre_update(self):
        pass
    
    def update(self):
        # don't apply physics to selected objects being dragged
        if self.physics_move and not (self.world.dragging_object and self in self.world.selected_objects):
            self.apply_move()
        self.update_state()
        self.update_state_sounds()
        if self.facing_changes_art:
            self.update_facing()
        # update collision shape before CollisionLord resolves any collisions
        self.collision.update()
    
    def update_renderables(self):
        # even if debug viz are off, update once on init to set correct state
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.update()
        if self.show_bounds or self in self.world.selected_objects:
            self.bounds_renderable.update()
        if self.show_collision and self.is_dynamic():
            self.collision.update_renderables()
        if self.visible:
            self.renderable.update()
    
    def get_debug_text(self):
        "subclass logic can return a string to display in debug line"
        return None
    
    def should_collide(self):
        return self.collision_type != CT_NONE and self.is_in_current_room()
    
    def is_in_room(self, room):
        return len(self.rooms) == 0 or room in self.rooms.values()
    
    def is_in_current_room(self):
        return len(self.rooms) == 0 or self.world.current_room in self.rooms.values()
    
    def render_debug(self):
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.render()
        if self.show_bounds or self in self.world.selected_objects:
            self.bounds_renderable.render()
        if self.show_collision and self.collision_type != CT_NONE:
            self.collision.render()
    
    def render(self, layer, z_override=None):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer, z_override)
    
    def get_dict(self):
        "return a dict that GameWorld.save_to_file can dump to JSON"
        d = { 'class_name': type(self).__name__ }
        # serialize whatever other vars are declared in self.serialized
        for prop_name in self.serialized:
            if hasattr(self, prop_name):
                d[prop_name] = getattr(self, prop_name)
        return d
    
    def reset_in_place(self):
        self.world.reset_object_in_place(self)
    
    def destroy(self):
        self.stop_all_sounds()
        self.rooms = {}
        if self in self.world.selected_objects:
            self.world.selected_objects.remove(self)
        self.origin_renderable.destroy()
        self.bounds_renderable.destroy()
        self.collision.destroy()
        for attachment in self.attachments:
            attachment.destroy()
        self.renderable.destroy()
        self.should_destroy = True


class GameObjectAttachment(GameObject):
    
    "GameObject that doesn't think about anything, just renders"
    
    collision_type = CT_NONE
    should_save = False
    selectable = False
    physics_move = False
    # offset from parent object's origin
    offset_x, offset_y, offset_z = 0., 0., 0.
    editable = GameObject.editable + ['offset_x', 'offset_y', 'offset_z']
    
    def attach_to(self, gobj):
        self.parent = gobj
    
    def update(self):
        if not self.art.updated_this_tick:
            self.art.update()
        self.x = self.parent.x + self.offset_x
        self.y = self.parent.y + self.offset_y
        self.z = self.parent.z + self.offset_z


class BlobShadow(GameObjectAttachment):
    art_src = 'blob_shadow'
    alpha = 0.5

class StaticTileBG(GameObject):
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    physics_move = False

class StaticTileObject(GameObject):
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    physics_move = False
    y_sort = True

class StaticBoxObject(GameObject):
    collision_shape_type = CST_AABB
    collision_type = CT_GENERIC_STATIC
    physics_move = False

class DynamicBoxObject(GameObject):
    collision_shape_type = CST_AABB
    collision_type = CT_GENERIC_DYNAMIC
    y_sort = True

class Pickup(GameObject):
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    y_sort = True
    attachment_classes = { 'shadow': 'BlobShadow' }

class GameCharacter(GameObject):
    
    state_changes_art = True
    stand_if_not_moving = True
    # move state name - added to valid_states in init so subclasses recognized
    move_state = 'walk'
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    
    def __init__(self, world, obj_data=None):
        if not self.move_state in self.valid_states:
            self.valid_states.append(self.move_state)
        GameObject.__init__(self, world, obj_data)
    
    def update_state(self):
        GameObject.update_state(self)
        if abs(self.vel_x) > 0.1 or abs(self.vel_y) > 0.1:
            self.state = self.move_state

class Player(GameCharacter):
    log_move = False
    collision_type = CT_PLAYER
    editable = GameCharacter.editable + ['move_accel_x', 'move_accel_y',
                                         'ground_friction', 'air_friction',
                                         'bounciness', 'stop_velocity']
    
    def pre_first_update(self):
        if self.world.player is None:
            self.world.player = self
            if self.world.player_camera_lock:
                self.world.camera.focus_object = self
            else:
                self.world.camera.focus_object = None
    
    def button_pressed(self, button_index):
        pass
    
    def button_unpressed(self, button_index):
        pass


class TopDownPlayer(Player):
    
    y_sort = True
    attachment_classes = { 'shadow': 'BlobShadow' }
    facing_changes_art = True
    
    def get_facing_dir(self):
        return FACING_DIRS[self.facing]


class WorldPropertiesObject(GameObject):
    
    "special magic singleton object that stores and sets GameWorld properties"
    
    art_src = 'world_properties_object'
    visible = deleteable = selectable = False
    locked = True
    physics_move = False
    do_not_list = True
    # properties we serialize on behalf of GameWorld
    # TODO: figure out how to make these defaults sync with those in GW?
    world_props = ['gravity_x', 'gravity_y', 'gravity_z',
                   'hud_class_name', 'globals_object_class_name',
                   'camera_x', 'camera_y', 'camera_z',
                   'bg_color_r', 'bg_color_g', 'bg_color_b', 'bg_color_a',
                   'player_camera_lock', 'object_grid_snap', 'draw_hud',
                   'collision_enabled', 'show_collision_all', 'show_bounds_all',
                   'show_origin_all'
    ]
    serialized = world_props
    # all visible properties are serialized, not editable
    editable = []
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        for v in self.serialized:
            if v in obj_data:
                # if world has property from loaded data, use it
                if hasattr(self.world, v):
                    setattr(self.world, v, obj_data[v])
                setattr(self, v, obj_data[v])
            # if world has property but loaded data doesn't, use world's
            elif hasattr(self.world, v):
                setattr(self, v, getattr(self.world, v))
            else:
                setattr(self, v, 0)
        # special handling of bg color (a list)
        self.world.bg_color = [self.bg_color_r, self.bg_color_g, self.bg_color_b, self.bg_color_a]
        self.world.camera.set_loc(self.camera_x, self.camera_y, self.camera_z)
    
    def set_object_property(self, prop_name, new_value):
        setattr(self, prop_name, new_value)
        # special handling for some values, eg bg color and camera
        if prop_name.startswith('bg_color_'):
            component = {'r': 0, 'g': 1, 'b': 2, 'a': 3}[prop_name[-1]]
            self.world.bg_color[component] = float(new_value)
        elif prop_name.startswith('camera_') and len(prop_name) == len('camera_x'):
            setattr(self.world.camera, prop_name[-1], new_value)
        # some properties have unique set methods in GW
        elif prop_name == 'show_collision_all':
            self.world.toggle_all_collision_viz()
        elif prop_name == 'show_bounds_all':
            self.world.toggle_all_bounds_viz()
        elif prop_name == 'show_origin_all':
            self.world.toggle_all_origin_viz()
        elif prop_name == 'player_camera_lock':
            self.world.toggle_player_camera_lock()
        # normal properties you can just set: set em
        elif hasattr(self.world, prop_name):
            setattr(self.world, prop_name, new_value)
    
    def update_from_world(self):
        self.camera_x = self.world.camera.x
        self.camera_y = self.world.camera.y
        self.camera_z = self.world.camera.z


class WorldGlobalsObject(GameObject):
    """
    invisible object holding global state, variables etc in GameWorld.globals
    subclass can be specified in WorldPropertiesObject
    NOTE: this object is spawned from scratch every load, it's never serialized!
    """
    should_save = False
    visible = deleteable = selectable = False
    locked = True
    do_not_list = True
    physics_move = False
    serialized = []
    editable = []


class StaticTileTrigger(GameObject):
    
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    noncolliding_classes = ['GameObject']
    physics_move = False
    
    def started_colliding(self, other):
        #self.app.log('Trigger overlapped with %s' % other.name)
        pass

class RoomWarpTrigger(StaticTileTrigger):
    destination_room = 'SOME_ROOM'
    serialized = StaticTileTrigger.serialized + ['destination_room']
    # if player overlaps, change room to destination_room
    # TODO: maybe also warp to a loc?
    def started_colliding(self, other):
        if isinstance(other, Player):
            self.world.change_room(self.destination_room)

class LocationMarker(GameObject):
    art_src = 'loc_marker'
    serialized = ['name', 'x', 'y', 'z', 'visible', 'locked']
    editable = []
    alpha = 0.5
    physics_move = False
