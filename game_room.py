
class GameRoom:
    
    # if set, camera will move to marker with this name when room entered
    camera_marker_name = ''
    serialized = ['name', 'camera_marker_name']
    # log changes to and from this room
    log_changes = False
    
    def __init__(self, world, name, room_data=None):
        self.world = world
        self.name = name
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
        if self.log_changes:
            self.world.app.log('Room "%s" entered' % self.name)
        # set camera if marker is set
        self.use_camera_marker()
        # tell objects in this room player has entered so eg spawners can fire
        for obj in self.objects.values():
            obj.room_entered(self, old_room)
    
    def exited(self, new_room):
        if self.log_changes:
            self.world.app.log('Room "%s" exited' % self.name)
        # tell objects in this room player has exited
        for obj in self.objects.values():
            obj.room_exited(self, new_room)
    
    def add_object_by_name(self, obj_name):
        obj = self.world.objects.get(obj_name, None)
        if not obj:
            self.world.app.log("Couldn't find object named %s" % obj_name)
            return
        self.add_object(obj)
    
    def add_object(self, obj):
        self.objects[obj.name] = obj
        obj.rooms[self.name] = self
    
    def remove_object_by_name(self, obj_name):
        obj = self.world.objects.get(obj_name, None)
        if not obj:
            self.world.app.log("Couldn't find object named %s" % obj_name)
            return
        self.remove_object(obj)
    
    def remove_object(self, obj):
        self.objects.pop(obj.name)
        obj.rooms.pop(self.name)
    
    def get_dict(self):
        "return a dict that GameWorld.save_to_file can dump to JSON"
        object_names = list(self.objects.keys())
        d = {'class_name': type(self).__name__, 'objects': object_names}
        # serialize whatever other vars are declared in self.serialized
        for prop_name in self.serialized:
            if hasattr(self, prop_name):
                d[prop_name] = getattr(self, prop_name)
        return d
    
    def destroy(self):
        if self.name in self.world.rooms:
            self.world.rooms.pop(self.name)
        # remove references to us in each of our objects
        for obj in self.objects.values():
            obj.rooms.pop(self.name)
        self.objects = {}
