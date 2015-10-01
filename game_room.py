
class GameRoom:
    
    def __init__(self, world, name):
        self.world = world
        self.name = name
        # dict of objects by name:object
        self.objects = {}
    
    def entered(self):
        self.world.app.log('Room %s entered' % self.name)
    
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
        d = { 'name': self.name, 'objects': object_names }
        d['class_name'] = type(self).__name__
        return d
    
    def destroy(self):
        # TODO: remove references to us in each of our objects
        pass
