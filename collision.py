
def a_push_b(a, b, contact):
    x = b.x + contact.normal.x * contact.distance
    y = b.y + contact.normal.y * contact.distance
    b.set_loc(x, y)
    #b.vel_x = 0
    #b.vel_y = 0

def player_vs_dynamic_begin(space, arbiter):
    obj1 = arbiter.shapes[0].gobj
    obj2 = arbiter.shapes[1].gobj
    #print('pymunk: %s collided with %s' % (obj1.name, obj2.name))
    a_push_b(obj1, obj2, arbiter.contacts[0])
    return True

def player_vs_dynamic_pre_solve(space, arbiter):
    player_vs_dynamic_begin(space, arbiter)
    return False

def player_vs_static_begin(space, arbiter):
    obj1 = arbiter.shapes[0].gobj
    obj2 = arbiter.shapes[1].gobj
    #print('pymunk: %s collided with %s' % (obj1.name, obj2.name))
    a_push_b(obj2, obj1, arbiter.contacts[0])
    return True

def player_vs_static_pre_solve(space, arbiter):
    player_vs_static_begin(space, arbiter)
    return False

def always_collide(space, arbiter):
    return True
