
from game_object import GameObject, FACING_DIRS
from collision import CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

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


class LocationMarker(GameObject):
    "very simple GameObject that marks an XYZ location for eg camera points"
    art_src = 'loc_marker'
    serialized = ['name', 'x', 'y', 'z', 'visible', 'locked']
    editable = []
    alpha = 0.5
    physics_move = False


class StaticTileTrigger(GameObject):
    
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    noncolliding_classes = ['GameObject']
    physics_move = False
    serialized = ['name', 'x', 'y', 'z', 'art_src', 'visible', 'locked']
    
    def started_colliding(self, other):
        #self.app.log('Trigger overlapped with %s' % other.name)
        pass

class WarpTrigger(StaticTileTrigger):
    "warps player to a room/marker when they touch it"
    art_src = 'trigger_default'
    # if set, warp to this location marker
    destination_marker_name = None
    # if set, make this room the world's current
    destination_room = None
    # if True, change to destination marker's room
    use_marker_room = True
    serialized = StaticTileTrigger.serialized + ['destination_room',
                                                 'destination_marker']
    def started_colliding(self, other):
        # if player overlaps, change room to destination_room
        if not isinstance(other, Player):
            return
        if self.destination_room:
            if other.warped_to_recently([self.world.current_room.name, self.destination_room]):
                return
            other.set_warping(self.destination_room, self.name)
            self.world.change_room(self.destination_room)
        elif self.destination_marker_name:
            if other.warped_to_recently([self.world.current_room.name, self.destination_marker_name]):
                return
            marker = self.world.objects[self.destination_marker_name]
            other.set_loc(marker.x, marker.y, marker.z)
            # warp to marker's room if specified, but only if it's only in one
            if self.use_marker_room and len(marker.rooms) == 1:
                room = random.choice(marker.rooms.values())
                # warn if both room and marker are set but they conflict
                if self.destination_room and room.name != self.destination_room:
                    self.log("Marker %s's room differs from destination room %s" % (marker.name, self.destination_room))
                other.set_warping(room.name, self.name)
                self.world.change_room(room)
            else:
                other.set_warping(self.destination_marker_name, self.name)


class ObjectSpawner(LocationMarker):
    "simple object that spawns an object when triggered"
    spawn_class_name = None
    spawn_obj_name = None
    # dict of properties to set on newly spawned object
    spawn_obj_data = {}
    # number of times we can fire, -1 = infinite
    times_to_fire = -1
    # if True, spawned object will be destroyed when player leaves its room
    destroy_on_room_exit = True
    serialized = LocationMarker.serialized + ['spawn_class_name', 'spawn_obj_name',
                                              'times_to_fire', 'destroy_on_room_exit'
    ]
    
    def __init__(self, world, obj_data=None):
        LocationMarker.__init__(self, world, obj_data)
        self.times_fired = 0
        # list of objects we've spawned
        self.spawned_objects = []
    
    def do_spawn(self):
        new_obj = self.world.spawn_object_of_class(self.spawn_class_name,
                                                   self.x, self.y)
        self.world.rename_object(new_obj, self.spawn_obj_name)
        # new object should be in same rooms as us
        new_obj.rooms.update(self.rooms)
        # TODO: put new object in our room(s), apply spawn_obj_data
    
    def room_entered(self, room, old_room):
        if self.times_to_fire != -1 and self.times_fired >= self.times_to_fire:
            return
        self.do_spawn()
        if self.times_fired != -1:
            self.times_fired += 1
    
    def room_exited(self, room, new_room):
        if not self.destroy_on_room_exit:
            return
        for obj in self.spawned_objects:
            obj.destroy()
