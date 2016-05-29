
from game_object import GameObject

class GameRoom:
    """
    A collection of GameObjects within a GameWorld. Can be used to limit scope
    of object updates, collisions, etc.
    """
    camera_marker_name = ''
    "If set, camera will move to marker with this name when room entered"
    camera_follow_player = False
    "If True, camera will follow player while in this room"
    left_edge_warp_dest_name, right_edge_warp_dest_name = '', ''
    "If set, warp to room OR marker with this name when edge crossed"
    top_edge_warp_dest_name, bottom_edge_warp_dest_name = '', ''
    warp_edge_bounds_obj_name = ''
    "Object whose art's bounds should be used as our \"edges\" for above"
    serialized = ['name', 'camera_marker_name', 'left_edge_warp_dest_name',
                  'right_edge_warp_dest_name', 'top_edge_warp_dest_name',
                  'bottom_edge_warp_dest_name', 'warp_edge_bounds_obj_name',
                  'camera_follow_player']
    "List of string names of members to serialize for this Room class."
    log_changes = False
    "Log changes to and from this room"
    def __init__(self, world, name, room_data=None):
        self.world = world
        self.name = name
        self.pre_first_update_run = False
        # dict of objects by name:object
        self.objects = {}
        if not room_data:
            return
        # restore serialized properties
        # TODO: this is copy-pasted from GameObject, find a way to unify
        # TODO: GameWorld.set_data_for that takes instance, serialized list, data dict
        for v in self.serialized:
            if not v in room_data:
                self.world.app.dev_log("Serialized property '%s' not found for room %s" % (v, self.name))
                continue
            if not hasattr(self, v):
                setattr(self, v, None)
            # match type of variable as declared, eg loc might be written as
            # an int in the JSON so preserve its floatness
            if getattr(self, v) is not None:
                src_type = type(getattr(self, v))
                setattr(self, v, src_type(room_data[v]))
            else:
                setattr(self, v, room_data[v])
        # find objects by name and add them
        for obj_name in room_data.get('objects', []):
            self.add_object_by_name(obj_name)
    
    def pre_first_update(self):
        self.reset_edge_warps()
    
    def reset_edge_warps(self):
        self.edge_obj = self.world.objects.get(self.warp_edge_bounds_obj_name, None)
        # no warping if we don't know our bounds
        if not self.edge_obj:
            return
        edge_dest_name_suffix = '_name'
        def set_edge_dest(dest_property):
            # property name to destination name
            dest_name = getattr(self, dest_property)
            # get room OR object with name
            dest_room = self.world.rooms.get(dest_name, None)
            dest_obj = self.world.objects.get(dest_name, None)
            # derive member name from serialized property name
            member_name = dest_property.replace(edge_dest_name_suffix, '')
            setattr(self, member_name, dest_room or dest_obj or None)
        for pname in ['left_edge_warp_dest_name', 'right_edge_warp_dest_name',
                      'top_edge_warp_dest_name', 'bottom_edge_warp_dest_name']:
            set_edge_dest(pname)
    
    def set_camera_marker_name(self, marker_name):
        if not marker_name in self.world.objects:
            self.world.app.log("Couldn't find camera marker with name %s" % marker_name)
            return
        self.camera_marker_name = marker_name
        if self is self.world.current_room:
            self.use_camera_marker()
    
    def use_camera_marker(self):
        if not self.camera_marker_name in self.world.objects:
            return
        cam_mark = self.world.objects[self.camera_marker_name]
        self.world.camera.set_loc_from_obj(cam_mark)
    
    def entered(self, old_room):
        "Run when the player enters this room."
        if self.log_changes:
            self.world.app.log('Room "%s" entered' % self.name)
        # set camera if marker is set
        if self.world.room_camera_changes_enabled:
            self.use_camera_marker()
        if self.camera_follow_player:
            self.world.enable_player_camera_lock()
        else:
            self.world.disable_player_camera_lock()
        # tell objects in this room player has entered so eg spawners can fire
        for obj in self.objects.values():
            obj.room_entered(self, old_room)
    
    def exited(self, new_room):
        "Run when the player exits this room."
        if self.log_changes:
            self.world.app.log('Room "%s" exited' % self.name)
        # tell objects in this room player has exited
        for obj in self.objects.values():
            obj.room_exited(self, new_room)
    
    def add_object_by_name(self, obj_name):
        "Add object with given name to this room."
        obj = self.world.objects.get(obj_name, None)
        if not obj:
            self.world.app.log("Couldn't find object named %s" % obj_name)
            return
        self.add_object(obj)
    
    def add_object(self, obj):
        "Add object (by reference) to this room."
        self.objects[obj.name] = obj
        obj.rooms[self.name] = self
    
    def remove_object_by_name(self, obj_name):
        "Remove object with given name from this room."
        obj = self.world.objects.get(obj_name, None)
        if not obj:
            self.world.app.log("Couldn't find object named %s" % obj_name)
            return
        self.remove_object(obj)
    
    def remove_object(self, obj):
        "Remove object (by reference) from this room."
        if obj.name in self.objects:
            self.objects.pop(obj.name)
        else:
            self.world.app.log("GameRoom %s doesn't contain GameObject %s" % (self.name, obj.name))
        if self.name in obj.rooms:
            obj.rooms.pop(self.name)
        else:
            self.world.app.log("GameObject %s not found in GameRoom %s" % (obj.name, self.name))
    
    def get_dict(self):
        "Return a dict that GameWorld.save_to_file can dump to JSON"
        object_names = list(self.objects.keys())
        d = {'class_name': type(self).__name__, 'objects': object_names}
        # serialize whatever other vars are declared in self.serialized
        for prop_name in self.serialized:
            if hasattr(self, prop_name):
                d[prop_name] = getattr(self, prop_name)
        return d
    
    def _check_edge_warp(self, game_object):
        # bail if no bounds or edge warp destinations set
        if not self.edge_obj:
            return
        if not self.left_edge_warp_dest and not self.right_edge_warp_dest and not self.top_edge_warp_dest and not self.bottom_edge_warp_dest:
            return
        if game_object.warped_recently():
            return
        px, py = game_object.x, game_object.y
        if self.edge_obj.is_point_inside(px, py):
            return
        left, top, right, bottom = self.edge_obj.get_edges()
        # which edge are we beyond?
        warp_dest = None
        if top > py > bottom and px < left:
            warp_dest = self.left_edge_warp_dest
        elif top > py > bottom and px > right:
            warp_dest = self.right_edge_warp_dest
        elif left < px < right and py > top:
            warp_dest = self.top_edge_warp_dest
        elif left < px < right and py < bottom:
            warp_dest = self.bottom_edge_warp_dest
        if not warp_dest:
            return
        if issubclass(type(warp_dest), GameRoom):
            self.world.change_room(warp_dest.name)
        elif issubclass(type(warp_dest), GameObject):
            # TODO: change room or not? use_marker_room flag a la WarpTrigger?
            game_object.set_loc(warp_dest.x, warp_dest.y)
        game_object.last_warp_update = self.world.updates
    
    def update(self):
        if self is self.world.current_room:
            self._check_edge_warp(self.world.player)
    
    def destroy(self):
        if self.name in self.world.rooms:
            self.world.rooms.pop(self.name)
        # remove references to us in each of our objects
        for obj in self.objects.values():
            obj.rooms.pop(self.name)
        self.objects = {}
