import os, math, random

from collections import namedtuple

import vector

from art import Art, ArtInstance
from renderable import GameObjectRenderable
from renderable_line import OriginIndicatorRenderable, BoundsIndicatorRenderable

from collision import Contact, Collideable, CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CTG_STATIC, CTG_DYNAMIC, point_in_box

# facings
GOF_LEFT = 0
"Object is facing left"
GOF_RIGHT = 1
"Object is facing right"
GOF_FRONT = 2
"Object is facing front"
GOF_BACK = 3
"Object is facing back"

FACINGS = {
    GOF_LEFT: 'left',
    GOF_RIGHT: 'right',
    GOF_FRONT: 'front',
    GOF_BACK: 'back'
}
"Dict mapping GOF_* facing enum values to strings"

FACING_DIRS = {
    GOF_LEFT: (-1, 0),
    GOF_RIGHT: (1, 0),
    GOF_FRONT: (0, -1),
    GOF_BACK: (0, 1)
}
"Dict mapping GOF_* facing enum values to (x,y) orientations"

DEFAULT_STATE = 'stand'

# timer slots
TIMER_PRE_UPDATE = 0
TIMER_UPDATE = 1
TIMER_POST_UPDATE = 2

__pdoc__ = {}
__pdoc__['GameObject.x'] = "Object's location in 3D space."


class GameObject:
    """
    Base class game object. GameObjects (GOs) are spawned into and managed by
    a GameWorld. All GOs render and collide via a single Renderable and
    Collideable, respectively. GOs can have states and facings. GOs are
    serialized in game state save files. Much of Playscii game creation involves
    creating flavors of GameObject.
    See game_util_object module for some generic subclasses for things like
    a player, spawners, triggers, attachments etc.
    """
    art_src = 'game_object_default'
    """
    If specified, this art file will be loaded from disk and used as object's
    default appearance. If object has states/facings, this is the "base"
    filename prefix, eg "hero" in "hero_stand_front.psci".
    """
    state_changes_art = False
    "If True, art will change with current state; depends on file naming."
    stand_if_not_moving = False
    "If True, object will go to stand state any time velocity is zero."
    valid_states = [DEFAULT_STATE]
    "List of valid states for this object, used to find anims"
    facing_changes_art = False
    "If True, art will change based on facing AND state"
    generate_art = False
    """
    If True, blank Art will be created with these dimensions, charset,
    and palette
    """
    use_art_instance = False
    "If True, always use an ArtInstance of source Art"
    animating = False
    "If True, object's Art will animate on init/reset"
    art_width, art_height = 8, 8
    art_charset, art_palette = None, None
    y_sort = False
    "If True, object will sort according to its Y position a la Zelda LttP"
    lifespan = 0.
    "If >0, object will self-destroy after this many seconds"
    kill_distance_from_origin = 1000
    """
    If object gets further than this distance from origin,
    (non-overridden) update will self-destroy
    """
    spawner = None
    "If another object spawned us, store reference to it here"
    physics_move = True
    "If False, don't do move physics updates for this object"
    fast_move_steps = 0
    """
    If >0, subdivide high-velocity moves into fractions-of-this-object-sized
    steps to avoid tunneling. turn this up if you notice an object tunneling.
    # 1 = each step is object's full size
    # 2 = each step is half object's size
    # N = each step is 1/N object's size
    """
    move_accel_x = move_accel_y = 200.
    "Acceleration per update from player movement"
    ground_friction = 10.0
    air_friction = 25.0
    mass = 1.
    "Mass: negative number = infinitely dense"
    bounciness = 0.25
    "Bounciness aka restitution, % of velocity reflected on bounce"
    stop_velocity = 0.1
    "Near-zero point at which any velocity is set to zero"
    log_move = False
    log_load = False
    log_spawn = False
    visible = True
    alpha = 1.
    locked = False
    "If True, location is protected from edit mode drags, can't click to select"
    show_origin = False
    show_bounds = False
    show_collision = False
    collision_shape_type = CST_NONE
    "Collision shape: tile, circle, AABB - see the CST_* enum values"
    collision_type = CT_NONE
    "Type of collision (static, dynamic)"
    col_layer_name = 'collision'
    "Collision layer name for CST_TILE objects"
    draw_col_layer = False
    "If True, collision layer will draw normally"
    col_offset_x, col_offset_y = 0., 0.
    "Collision circle/box offset from origin"
    col_radius = 1.
    "Collision circle size, if CST_CIRCLE"
    col_width, col_height = 1., 1.
    "Collision AABB size, if CST_AABB"
    art_off_pct_x, art_off_pct_y = 0.5, 0.5
    """
    Art offset from pivot: Renderable's origin_pct set to this if not None
    0,0 = top left; 1,1 = bottom right; 0.5,0.5 = center
    """
    should_save = True
    "If True, write this object to state save files"
    serialized = ['name', 'x', 'y', 'z', 'art_src', 'visible', 'locked', 'y_sort',
                  'art_off_pct_x', 'art_off_pct_y', 'alpha', 'state', 'facing',
                  'animating', 'scale_x', 'scale_y']
    "List of members to serialize (no weak refs!)"
    editable = ['show_collision', 'col_radius', 'col_width', 'col_height',
                'mass', 'bounciness', 'stop_velocity']
    """
    Members that don't need to be serialized, but should be exposed to
    object edit UI
    """
    set_methods = {'art_src': 'set_art_src', 'alpha': '_set_alpha',
                   'scale_x': '_set_scale_x', 'scale_y': '_set_scale_y',
                   'name': '_rename', 'col_radius': '_set_col_radius',
                   'col_width': '_set_col_width',
                   'col_height': '_set_col_height'
    }
    "If setting a given member should run some logic, specify the method here"
    selectable = True
    "If True, user can select this object in edit mode"
    deleteable = True
    "If True, user can delete this object in edit mode"
    is_debug = False
    "If True, object's visibility can be toggled with View menu option"
    exclude_from_object_list = False
    "If True, do not list object in edit mode UI - system use only!"
    exclude_from_class_list = False
    "If True, do not list class in edit mode UI - system use only!"
    attachment_classes = {}
    "Objects to spawn as attachments: key is member name, value is class"
    noncolliding_classes = []
    "Blacklist of string names for classes to ignore collisions with"
    sound_filenames = {}
    'Dict of sound filenames, keys are string "tags"'
    looping_state_sounds = {}
    "Dict of looping sounds that should play while in a given state"
    update_if_outside_room = False
    """
    If True, object's update function will run even if it's
    outside the world's current room
    """
    handle_key_events = False
    "If True, handle key input events passed in from world / input handler"
    handle_mouse_events = False
    "If True, handle mouse click/wheel events passed in from world / input handler"
    consume_mouse_events = False
    "If True, prevent any other mouse click/wheel events from being processed"
    def __init__(self, world, obj_data=None):
        """
        Create new GameObject in world, from serialized data if provided.
        """
        self.x, self.y, self.z = 0., 0., 0.
        "Object's location in 3D space."
        self.scale_x, self.scale_y, self.scale_z = 1., 1., 1.
        "Object's scale in 3D space."
        self.rooms = {}
        "Dict of rooms we're in - if empty, object appears in all rooms"
        self.state = DEFAULT_STATE
        "String representing object state. Every object has one, even if it never changes."
        self.facing = GOF_FRONT
        "Every object gets a facing, even if it never changes"
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
        "Object's velocity in units per second. Derived from acceleration."
        self.move_x, self.move_y = 0, 0
        "User-intended acceleration"
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        self.last_update_end = 0
        self.flip_x = False
        "Set by state, True if object's renderable should be flipped in X axis."
        self.world = world
        "GameWorld this object is managed by"
        self.app = self.world.app
        "For convenience, Application instance for this object's GameWorld"
        self.destroy_time = 0
        "If >0, object will self-destroy at/after this time (in milliseconds)"
        # lifespan property = easy auto-set for fixed lifetime objects
        if self.lifespan > 0:
            self.set_destroy_timer(self.lifespan)
        self.timer_functions_pre_update = {}
        "Dict of running GameObjectTimerFuctions that run during pre_update"
        self.timer_functions_update = {}
        "Dict of running GameObjectTimerFuctions that run during update"
        self.timer_functions_post_update = {}
        "Dict of running GameObjectTimerFuctions that run during post_update"
        self.last_update_failed = False
        "When True, object's last update threw an exception"
        # load/create assets
        self.arts = {}
        "Dict of all Arts this object can reference, eg for states"
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
        "Renderable for debug drawing of object origin."
        self.bounds_renderable = BoundsIndicatorRenderable(self.app, self)
        "1px LineRenderable showing object's bounding box"
        for art in self.arts.values():
            if not art in self.world.art_loaded:
                self.world.art_loaded.append(art)
        self.orig_collision_type = self.collision_type
        "Remember last collision type for enable/disable - don't set manually!"
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
        "If True, object will be destroyed on next world update."
        self.pre_first_update_run = False
        "Flag that tells us we should run post_init next update."
        self.last_state = None
        self.last_warp_update = -1
        "Most recent warp world update, to prevent thrashing"
        # set up art instance only after all art/renderable init complete
        if self.use_art_instance:
            self.set_art(ArtInstance(self.art))
        if self.animating and self.art.frames > 0:
            self.start_animating()
        if self.log_spawn:
            self.app.log('Spawned %s with Art %s' % (self.name, os.path.basename(self.art.filename)))
    
    def get_unique_name(self):
        "Generate and return a somewhat human-readable unique name for object"
        name = str(self)
        return '%s_%s' % (type(self).__name__, name[name.rfind('x')+1:-1])
    
    def _rename(self, new_name):
        # pass thru to world, this method exists for edit set method
        self.world.rename_object(self, new_name)
    
    def pre_first_update(self):
        """
        Run before first update; use this for any logic that depends on
        init/creation being done ie all objects being present.
        """
        pass
    
    def load_arts(self):
        "Fill self.arts dict with Art references for eg states and facings."
        self.art = self.app.load_art(self.art_src, False)
        if self.art:
            self.arts[self.art_src] = self.art
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
        "Return True if given point is inside our bounds"
        left, top, right, bottom = self.get_edges()
        return point_in_box(x, y, left, top, right, bottom)
    
    def get_edges(self):
        "Return coords of our bounds (left, top, right, bottom)"
        left = self.x - (self.renderable.width * self.art_off_pct_x)
        right = self.x + (self.renderable.width * (1 - self.art_off_pct_x))
        top = self.y + (self.renderable.height * self.art_off_pct_y)
        bottom = self.y - (self.renderable.height * (1 - self.art_off_pct_y))
        return left, top, right, bottom
    
    def distance_to_object(self, other):
        "Return distance from center of this object to center of given object."
        return self.distance_to_point(other.x, other.y)
    
    def distance_to_point(self, point_x, point_y):
        "Return distance from center of this object to given point."
        dx = self.x - point_x
        dy = self.y - point_y
        return math.sqrt(dx ** 2 + dy ** 2)
    
    def normal_to_object(self, other):
        "Return tuple normal pointing in direction of given object."
        return self.normal_to_point(other.x, other.y)
    
    def normal_to_point(self, point_x, point_y):
        "Return tuple normal pointing in direction of given point."
        dist = self.distance_to_point(point_x, point_y)
        dx, dy = point_x - self.x, point_y - self.y
        if dist == 0:
            return 0, 0
        inv_dist = 1 / dist
        return dx * inv_dist, dy * inv_dist
    
    def get_render_offset(self):
        "Return a custom render offset. Override this in subclasses as needed."
        return 0, 0, 0
    
    def is_dynamic(self):
        "Return True if object is dynamic."
        return self.collision_type in CTG_DYNAMIC
    
    def is_entering_state(self, state):
        "Return True if object is in given state this frame but not last frame."
        return self.state == state and self.last_state != state
    
    def is_exiting_state(self, state):
        "Return True if object is in given state last frame but not this frame."
        return self.state != state and self.last_state == state
    
    def play_sound(self, sound_name, loops=0, allow_multiple=False):
        "Start playing given sound."
        # use sound_name as filename if it's not in our filenames dict
        sound_filename = self.sound_filenames.get(sound_name, sound_name)
        sound_filename = self.world.sounds_dir + sound_filename
        self.world.app.al.object_play_sound(self, sound_filename,
                                            loops, allow_multiple)
    
    def stop_sound(self, sound_name):
        "Stop playing given sound."
        sound_filename = self.sound_filenames.get(sound_name, sound_name)
        sound_filename = self.world.sounds_dir + sound_filename
        self.world.app.al.object_stop_sound(self, sound_filename)
    
    def stop_all_sounds(self):
        "Stop all sounds playing on object."
        self.world.app.al.object_stop_all_sounds(self)
    
    def enable_collision(self):
        "Enable this object's collision."
        self.collision_type = self.orig_collision_type
    
    def disable_collision(self):
        "Disable this object's collision."
        if self.collision_type == CT_NONE:
            return
        # remember prior collision type
        self.orig_collision_type = self.collision_type
        self.collision_type = CT_NONE
    
    def started_overlapping(self, other):
        """
        Run when object begins overlapping with, but does not collide with,
        another object.
        """
        pass
    
    def started_colliding(self, other):
        "Run when object begins colliding with another object."
        self.resolve_collision_momentum(other)
    
    def stopped_colliding(self, other):
        "Run when object stops colliding with another object."
        if not other.name in self.collision.contacts:
            # TODO: understand why this spams when player has a MazePickup
            #self.world.app.log("%s stopped colliding with %s but wasn't in its contacts!" % (self.name, other.name))
            return
        # called from check_finished_contacts
        self.collision.contacts.pop(other.name)
    
    def resolve_collision_momentum(self, other):
        "Resolve velocities between this object and given other object."
        # don't resolve a pair twice
        if self in self.world.cl.collisions_this_frame:
            return
        # determine new direction and velocity
        total_vel = self.vel_x + self.vel_y + other.vel_x + other.vel_y
        # negative mass = infinite
        total_mass = max(0, self.mass) + max(0, other.mass)
        if other.name not in self.collision.contacts or \
           self.name not in other.collision.contacts:
            return
        # redistribute velocity based on mass we're colliding with
        if self.is_dynamic() and self.mass >= 0:
            ax = self.collision.contacts[other.name].overlap.x
            ay = self.collision.contacts[other.name].overlap.y
            a_vel = total_vel * (self.mass / total_mass)
            a_vel *= self.bounciness
            self.vel_x, self.vel_y = -ax * a_vel, -ay * a_vel
        if other.is_dynamic() and other.mass >= 0:
            bx = other.collision.contacts[self.name].overlap.x
            by = other.collision.contacts[self.name].overlap.y
            b_vel = total_vel * (other.mass / total_mass)
            b_vel *= other.bounciness
            other.vel_x, other.vel_y = -bx * b_vel, -by * b_vel
        # mark objects as resolved
        self.world.cl.collisions_this_frame.append(self)
        self.world.cl.collisions_this_frame.append(other)
    
    def check_finished_contacts(self):
        """
        Updates our Collideable's contacts dict for contacts that were
        happening last update but not this one, and call stopped_colliding.
        """
        # put stopped-colliding objects in a list to process after checks
        finished = []
        # keep separate list of names of objects no longer present
        destroyed = []
        for obj_name,contact in self.collision.contacts.items():
            if contact.timestamp < self.world.cl.ticks:
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
        "Return list of all objects we're currently contacting."
        return [self.world.objects[obj] for obj in self.collision.contacts]
    
    def get_collisions(self):
        "Return list of all overlapping shapes our shapes should collide with."
        overlaps = []
        for shape in self.collision.shapes:
            for other in self.world.cl.dynamic_shapes:
                if other.go is self:
                    continue
                if not other.go.should_collide():
                    continue
                if not self.can_collide_with(other.go):
                    continue
                if not other.go.can_collide_with(self):
                    continue
                overlaps.append(shape.get_overlap(other))
            for other in shape.get_overlapping_static_shapes():
                overlaps.append(other)
        return overlaps
    
    def is_overlapping(self, other):
        "Return True if we overlap with other object's collision"
        return other.name in self.collision.contacts
    
    def are_bounds_overlapping(self, other):
        "Return True if we overlap with other object's Art's bounds"
        left, top, right, bottom = self.get_edges()
        for x,y in [(left, top), (right, top), (right, bottom), (left, bottom)]:
            if other.is_point_inside(x, y):
                return True
        return False
    
    def get_tile_at_point(self, point_x, point_y):
        "Return x,y tile coord for given worldspace point"
        left, top, right, bottom = self.get_edges()
        x = (point_x - left) / self.art.quad_width
        x = math.floor(x)
        y = (point_y - top) / self.art.quad_height
        y = math.ceil(-y)
        return x, y
    
    def get_tiles_overlapping_box(self, box_left, box_top, box_right, box_bottom, log=False):
        "Returns x,y coords for each tile overlapping given box"
        if self.collision_shape_type != CST_TILE:
            return []
        left, top = self.get_tile_at_point(box_left, box_top)
        right, bottom = self.get_tile_at_point(box_right, box_bottom)
        if bottom < top:
            top, bottom = bottom, top
        # stay in bounds
        left = max(0, left)
        right = min(right, self.art.width - 1)
        top = max(1, top)
        bottom = min(bottom, self.art.height)
        tiles = []
        # account for range start being inclusive, end being exclusive
        for x in range(left, right + 1):
            for y in range(top - 1, bottom):
                tiles.append((x, y))
        return tiles
    
    def overlapped(self, other, overlap):
        """
        Called by CollisionLord when two objects overlap.
        returns: bool "overlap allowed", bool "collision starting"
        """
        started = other.name not in self.collision.contacts
        # create or update contact info: (overlap, timestamp)
        self.collision.contacts[other.name] = Contact(overlap,
                                                      self.world.cl.ticks)
        can_collide = self.can_collide_with(other)
        if not can_collide and started:
            self.started_overlapping(other)
        return can_collide, started
    
    def get_tile_loc(self, tile_x, tile_y, tile_center=True):
        "Return top left / center of current Art's tile in world coordinates"
        left, top, right, bottom = self.get_edges()
        x = left
        x += self.art.quad_width * tile_x
        y = top
        y -= self.art.quad_height * tile_y
        if tile_center:
            x += self.art.quad_width / 2
            y -= self.art.quad_height / 2
        return x, y
    
    def get_layer_z(self, layer_name):
        "Return Z of layer with given name"
        return self.z + self.art.layers_z[self.art.layer_names.index(layer_name)]
    
    def get_all_art(self):
        "Return a list of all Art used by this object"
        return list(self.arts.keys())
    
    def start_animating(self):
        "Start animation playback."
        self.renderable.start_animating()
    
    def stop_animating(self):
        "Pause animation playback on current frame."
        self.renderable.stop_animating()
    
    def set_object_property(self, prop_name, new_value):
        "Set property by given name to given value."
        if not hasattr(self, prop_name):
            return
        if prop_name in self.set_methods:
            method = getattr(self, self.set_methods[prop_name])
            method(new_value)
        else:
            setattr(self, prop_name, new_value)
    
    def get_art_for_state(self, state=None):
        "Return Art (and 'flip X' bool) that best represents current state"
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
                #assert(default_name in self.arts
                # don't assert - if base+state name available, use that
                if default_name in self.arts:
                    return self.arts[default_name], False
                else:
                    #self.app.log('%s: Art with name %s not available, using %s' % (self.name, default_name, self.art_src))
                    return self.arts[self.art_src], False
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
        #assert(has_front or has_sides)
        if not has_front and not has_sides:
            return self.arts[self.art_src], False
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
        "Set object to use new given Art (passed by reference)."
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
        "Set object to use new given Art (passed by filename)"
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
        "Set this object's location."
        self.x, self.y = x, y
        self.z = z or 0
    
    def reset_last_loc(self):
        'Reset "last location" values used for updating state and fast_move'
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
    
    def set_scale(self, x, y, z):
        "Set this object's scale."
        self.scale_x, self.scale_y, self.scale_z = x, y, z
        self.renderable.scale_x = self.scale_x
        self.renderable.scale_y = self.scale_y
        self.renderable.reset_size()
    
    def _set_scale_x(self, new_x):
        self.set_scale(new_x, self.scale_y, self.scale_z)
    
    def _set_scale_y(self, new_y):
        self.set_scale(self.scale_x, new_y, self.scale_z)
    
    def _set_col_radius(self, new_radius):
        self.col_radius = new_radius
        self.collision.shapes[0].radius = new_radius
    
    def _set_col_width(self, new_width):
        self.col_width = new_width
        self.collision.shapes[0].halfwidth = new_width / 2
    
    def _set_col_height(self, new_height):
        self.col_height = new_height
        self.collision.shapes[0].halfheight = new_height / 2
    
    def _set_alpha(self, new_alpha):
        self.renderable.alpha = self.alpha = new_alpha
    
    def allow_move(self, dx, dy):
        "Return True only if this object is allowed to move based on input."
        return True
    
    def allow_move_x(self, dx):
        "Return True if given movement in X axis is allowed."
        return True
    
    def allow_move_y(self, dy):
        "Return True if given movement in Y axis is allowed."
        return True
    
    def move(self, dir_x, dir_y):
        """
        Input player/sim-initiated velocity. Given value is multiplied by
        acceleration in get_acceleration.
        """
        # don't handle moves while game paused
        # (add override flag if this becomes necessary)
        if self.world.paused:
            return
        # check allow_move first
        if not self.allow_move(dir_x, dir_y):
            return
        if self.allow_move_x(dir_x):
            self.move_x += dir_x
        if self.allow_move_y(dir_y):
            self.move_y += dir_y
    
    def is_on_ground(self):
        '''
        Return True if object is "on the ground". Subclasses define custom
        logic here.
        '''
        return True
    
    def get_friction(self):
        "Return friction that should be applied for object's current context."
        return self.ground_friction if self.is_on_ground() else self.air_friction
    
    def is_affected_by_gravity(self):
        "Return True if object should be affected by gravity."
        return False
    
    def get_gravity(self):
        "Return x,y,z force of gravity for object's current context."
        return self.world.gravity_x, self.world.gravity_y, self.world.gravity_z
    
    def get_acceleration(self, vel_x, vel_y, vel_z):
        """
        Return x,y,z acceleration values for object's current context.
        """
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
        return vector.cut_xyz(accel_x, accel_y, accel_z, 0.01)
    
    def apply_move(self):
        """
        Apply current acceleration / velocity to position using Verlet
        integration with half-step velocity estimation.
        """
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
        self.vel_x, self.vel_y, self.vel_z = vector.cut_xyz(self.vel_x, self.vel_y, self.vel_z, self.stop_velocity)
    
    def moved_this_frame(self):
        "Return True if object changed locations this frame."
        delta = math.sqrt(abs(self.last_x - self.x) ** 2 + abs(self.last_y - self.y) ** 2 + abs(self.last_z - self.z) ** 2)
        return delta > self.stop_velocity
    
    def warped_recently(self):
        "Return True if object warped during last update."
        return self.world.updates - self.last_warp_update <= 0
    
    def handle_key_down(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        """
        Handle "key pressed" event, with keyboard mods passed in.
        GO subclasses can do stuff here if their handle_key_events=True
        """
        pass
    
    def handle_key_up(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        """
        Handle "key released" event, with keyboard mods passed in.
        GO subclasses can do stuff here if their handle_key_events=True
        """
        pass
    
    def clicked(self, button, mouse_x, mouse_y):
        """
        Handle mouse button down event, with button # and
        click location (in world coordinates) passed in.
        GO subclasses can do stuff here if their handle_mouse_events=True
        """
        pass
    
    def unclicked(self, button, mouse_x, mouse_y):
        """
        Handle mouse button up event, with button # and
        click location (in world coordinates) passed in.
        GO subclasses can do stuff here if their handle_mouse_events=True
        """
        pass
    
    def hovered(self, mouse_x, mouse_y):
        """
        Handle mouse hover (fires when object -starts- being hovered).
        GO subclasses can do stuff here if their handle_mouse_events=True
        """
        pass
    
    def unhovered(self, mouse_x, mouse_y):
        """
        Handle mouse unhover.
        GO subclasses can do stuff here if their handle_mouse_events=True
        """
        pass
    
    def mouse_wheeled(self, wheel_y):
        """
        Handle mouse wheel movement.
        GO subclasses can do stuff here if their handle_mouse_events=True
        """
        pass
    
    def set_timer_function(self, timer_name, timer_function, delay_min,
                           delay_max=0, repeats=-1, slot=TIMER_PRE_UPDATE):
        """
        Run given function in X seconds or every X seconds Y times.
        If max is given, next execution will be between min and max time.
        if repeat is -1, run indefinitely.
        "Slot" determines whether function will run in pre_update, update, or
        post_update.
        """
        timer = GameObjectTimerFunction(self, timer_name, timer_function,
                                        delay_min, delay_max, repeats, slot)
        # add to slot-appropriate dict
        d = [self.timer_functions_pre_update, self.timer_functions_update,
             self.timer_functions_post_update][slot]
        d[timer_name] = timer
    
    def stop_timer_function(self, timer_name):
        "Stop currently running timer function with given name."
        timer = self.timer_functions_pre_update.get(timer_name, None) or \
                self.timer_functions_update.get(timer_name, None) or \
                self.timer_functions_post_update.get(timer_name, None)
        if not timer:
            self.app.log('Timer named %s not found on object %s' % (timer_name,
                                                                    self.name))
        d = [self.timer_functions_pre_update, self.timer_functions_update,
             self.timer_functions_post_update][timer.slot]
        d.pop(timer_name)
    
    def update_state(self):
        "Update object state based on current context, eg movement."
        if self.state_changes_art and self.stand_if_not_moving and \
           not self.moved_this_frame():
            self.state = DEFAULT_STATE
    
    def update_facing(self):
        "Update object facing based on current context, eg movement."
        dx, dy = self.x - self.last_x, self.y - self.last_y
        if dx == 0 and dy == 0:
            return
        # TODO: flag for "side view only" objects
        if abs(dy) > abs(dx):
            self.facing = GOF_BACK if dy >= 0 else GOF_FRONT
        else:
            self.facing = GOF_RIGHT if dx >= 0 else GOF_LEFT
    
    def update_state_sounds(self):
        "Stop and play looping sounds appropriate to current/recent states."
        for state,sound in self.looping_state_sounds.items():
            if self.is_entering_state(state):
                self.play_sound(sound, loops=-1)
            elif self.is_exiting_state(state):
                self.stop_sound(sound)
    
    def frame_begin(self):
        "Run at start of game loop iteration, before input/update/render."
        self.move_x, self.move_y = 0, 0
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        # if we're just entering stand state, play any sound for it
        if self.last_state is None:
            self.update_state_sounds()
        self.last_state = self.state
    
    def frame_update(self):
        "Run once per frame, after input + simulation update and before render."
        if not self.art.updated_this_tick:
            self.art.update()
        # update art based on state (and possibly facing too)
        if self.state_changes_art:
            new_art, flip_x = self.get_art_for_state()
            self.set_art(new_art)
            self.flip_x = flip_x
    
    def pre_update(self):
        "Run before any objects have updated this simulation tick."
        pass
    
    def post_update(self):
        "Run after all objects have updated this simulation tick."
        pass
    
    def fast_move(self):
        """
        Subdivide object's move this frame into steps to avoid tunneling.
        Only called for objects with fast_move_steps >0.
        """
        final_x, final_y = self.x, self.y
        dx, dy = self.x - self.last_x, self.y - self.last_y
        total_move_dist = math.sqrt(dx ** 2 + dy ** 2)
        if total_move_dist == 0:
            return
        # get movement normal
        inv_dist = 1 / total_move_dist
        dir_x, dir_y = dx * inv_dist, dy * inv_dist
        if self.collision_shape_type == CST_CIRCLE:
            step_dist = self.col_radius * 2
        elif self.collision_shape_type == CST_AABB:
            # get size in axis object is moving in
            step_x, step_y = self.col_width * dir_x, self.col_height * dir_y
            step_dist = math.sqrt(step_x ** 2 + step_y ** 2)
        step_dist /= self.fast_move_steps
        # if object isn't moving fast enough, don't step
        if total_move_dist <= step_dist:
            return
        steps = int(total_move_dist / step_dist)
        # start stepping from beginning of this frame's move distance
        self.x, self.y = self.last_x, self.last_y
        for i in range(steps):
            self.x += dir_x * step_dist
            self.y += dir_y * step_dist
            collisions = self.get_collisions()
            # if overlapping just leave as-is, collision update will resolve
            if len(collisions) > 0:
                return
        # ran through all steps without a hit, set back to final position
        self.x, self.y = final_x, final_y
    
    def get_time_since_last_update(self):
        "Return time (in milliseconds) since end of this object's last update."
        return self.world.get_elapsed_time() - self.last_update_end
    
    def update(self):
        """
        Apply movement/physics, update state and facing, keep our Collideable's
        location locked to us. Self-destroy if a timer is up or we've fallen
        out of the world.
        """
        if 0 < self.destroy_time <= self.world.get_elapsed_time():
            self.destroy()
        # don't apply physics to selected objects being dragged
        if self.physics_move and not self.name in self.world.drag_objects:
            self.apply_move()
        if self.fast_move_steps > 0:
            self.fast_move()
        self.update_state()
        self.update_state_sounds()
        if self.facing_changes_art:
            self.update_facing()
        # update collision shape before CollisionLord resolves any collisions
        self.collision.update()
        if abs(self.x) > self.kill_distance_from_origin or \
           abs(self.y) > self.kill_distance_from_origin:
            self.app.log('%s reached %s from origin, destroying.' % (self.name, self.kill_distance_from_origin))
            self.destroy()
    
    def update_renderables(self):
        """
        Keep our Renderable's location locked to us, and update any debug
        Renderables (collision, bounds etc) similarly.
        """
        # even if debug viz are off, update once on init to set correct state
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.update()
        if self.show_bounds or self in self.world.selected_objects or \
           (self is self.world.hovered_focus_object and self.selectable):
            self.bounds_renderable.update()
        if self.show_collision and self.is_dynamic():
            self.collision.update_renderables()
        if self.visible:
            self.renderable.update()
    
    def get_debug_text(self):
        "Subclass logic can return a string to display in debug line."
        return None
    
    def should_collide(self):
        "Return True if this object should collide in current context."
        return self.collision_type != CT_NONE and self.is_in_current_room()
    
    def can_collide_with(self, other):
        "Return True if this object is allowed to collide with given object."
        for ncc_name in self.noncolliding_classes:
            if isinstance(other, self.world.classes[ncc_name]):
                return False
        return True
    
    def is_in_room(self, room):
        "Return True if this object is in the given (by reference) Room."
        return len(self.rooms) == 0 or room.name in self.rooms
    
    def is_in_current_room(self):
        "Return True if this object is in the world's currently active Room."
        return len(self.rooms) == 0 or (self.world.current_room and self.world.current_room.name in self.rooms)
    
    def room_entered(self, room, old_room):
        "Run when a room we're in is entered."
        pass
    
    def room_exited(self, room, new_room):
        "Run when a room we're in is exited."
        pass
    
    def render_debug(self):
        "Render debug lines, eg origin/bounds/collision."
        # only show debug stuff if in edit mode
        if not self.world.app.ui.is_game_edit_ui_visible():
            return
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.render()
        if self.show_bounds or self in self.world.selected_objects or \
           (self.selectable and self is self.world.hovered_focus_object):
            self.bounds_renderable.render()
        if self.show_collision and self.collision_type != CT_NONE:
            self.collision.render()
    
    def render(self, layer, z_override=None):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer, z_override)
    
    def get_dict(self):
        """
        Return a dict serializing this object's state that
        GameWorld.save_to_file can dump to JSON. Only properties defined in
        this object's "serialized" list are stored. Direct object references
        are not safe to serialize, use only primitive types like strings.
        """
        d = { 'class_name': type(self).__name__ }
        # serialize whatever other vars are declared in self.serialized
        for prop_name in self.serialized:
            if hasattr(self, prop_name):
                d[prop_name] = getattr(self, prop_name)
        return d
    
    def reset_in_place(self):
        "Run GameWorld.reset_object_in_place on this object."
        self.world.reset_object_in_place(self)
    
    def set_destroy_timer(self, destroy_in_seconds):
        "Set object to destroy itself given number of seconds from now."
        self.destroy_time = self.world.get_elapsed_time() + destroy_in_seconds * 1000
    
    def destroy(self):
        self.stop_all_sounds()
        # remove rooms' references to us
        for room in self.rooms.values():
            if self.name in room.objects:
                room.objects.pop(self.name)
        self.rooms = {}
        if self in self.world.selected_objects:
            self.world.selected_objects.remove(self)
        if self.spawner:
            if hasattr(self.spawner, 'spawned_objects') and \
               self in self.spawner.spawned_objects:
                self.spawner.spawned_objects.remove(self)
        self.origin_renderable.destroy()
        self.bounds_renderable.destroy()
        self.collision.destroy()
        for attachment in self.attachments:
            attachment.destroy()
        self.renderable.destroy()
        self.should_destroy = True


class GameObjectTimerFunction:
    """
    Object that manages a function's execution schedule for a GameObject.
    Use GameObject.set_timer_function to create these.
    """
    def __init__(self, go, name, function, delay_min, delay_max, repeats, slot):
        self.go = go
        "GameObject using this timer"
        self.name = name
        "This timer's name"
        self.function = function
        "GO function to run"
        self.delay_min = delay_min
        "Delay before next execution"
        self.delay_max = delay_max
        "If specified, next execution will be between min and max"
        self.repeats = repeats
        "# of times to repeat. -1 = infinite"
        self.slot = slot
        "Execute before, during, or after object's update"
        self.next_update = self.go.world.get_elapsed_time()
        self.runs = 0
        self._set_next_time()
    
    def _set_next_time(self):
        "Compute and set this timer's next update time"
        # if no max delay, just use min, else rand(min, max)
        if not self.delay_max or self.delay_max == 0:
            delay = self.delay_min
        else:
            delay = random.random() * (self.delay_max - self.delay_min)
            delay += self.delay_min
        self.next_update += int(delay * 1000)
    
    def update(self):
        "Check timer, running function as needed"
        if self.go.world.get_elapsed_time() < self.next_update:
            return
        # TODO: if function needs to run multiple times, do that and update appropriately
        self._execute()
        # remove timer if it's executed enough already
        if self.repeats != -1 and self.runs > self.repeats:
            self.go.stop_timer_function(self.name)
        else:
            self._set_next_time()
    
    def _execute(self):
        # pass our object into our function
        self.function()
        self.runs += 1
