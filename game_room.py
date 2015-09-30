
class GameRoom:
    
    def __init__(self, world, name):
        self.world = world
        self.name = name
        # dict of objects by name:object
        self.objects = {}
    
    def add_object_by_name(self, obj_name):
        obj = self.world.objects[obj_name]
        self.add_object(obj)
    
    def add_object(self, obj):
        self.objects[obj.name] = obj
        obj.rooms[self.name] = self
    
    def remove_object_by_name(self, obj_name):
        obj = self.world.objects[obj_name]
        self.remove_object(obj)
    
    def remove_object(self, obj):
        self.objects.pop(obj.name)
        obj.rooms.pop(self.name)
    
    def destroy(self):
        # TODO: remove references to us in each of our objects
        pass
