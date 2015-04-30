
# collision types
CT_NONE = 0
CT_TILE = 1
CT_CIRCLE = 2
CT_AABB = 3

class CollisionLord:
    
    def __init__(self, app):
        self.app = app
    
    def update(self):
        for obj in self.app.game_objects:
            if not obj.dynamic:
                continue
            if not obj.transformed_this_frame:
                continue
            if obj.collision_type == CT_NONE:
                continue
            if obj.collision_type == CT_TILE:
                print('%s: collision type CT_TILE not handled yet!' % obj.name)
                continue
            for other in self.app.game_objects:
                if other is obj:
                    continue
                if other.collision_type == CT_NONE:
                    continue
                # broadphase
                boxes_overlap = do_boxes_overlap(obj, other)
                if not boxes_overlap:
                    continue
                # debug junk
                l1 = '%s topleft %.4f, %.4f bottomright %.4f, %.4f' % (obj.name, obj.left_x, obj.top_y, obj.right_x, obj.bottom_y)
                l2 = '%s topleft %.4f, %.4f bottomright %.4f, %.4f' % (other.name, other.left_x, other.top_y, other.right_x, other.bottom_y)
                lines = [l1, l2]
                overlap_x, overlap_y = get_overlap_loc(obj, other)
                if not overlap_x:
                    self.app.ui.debug_text.post_lines(lines)
                    continue
                lines += ['%s and %s overlap at %s,%s' % (obj.name, other.name, overlap_x, overlap_y)]
                self.app.ui.debug_text.post_lines(lines)
                # TODO: resolve overlaps, collisions based on class whitelists

def do_boxes_overlap(obj_a, obj_b):
    # GameObjects update their collision bounding boxes at end of update()
    if obj_b.left_x < obj_a.left_x < obj_b.right_x:
        return True
    elif obj_b.left_x < obj_a.right_x < obj_b.right_x:
        return True
    elif obj_b.top_y < obj_a.top_y < obj_b.bottom_y:
        return True
    elif obj_b.top_y < obj_a.bottom_y < obj_b.bottom_y:
        return True
    return False

def get_bb_tile_overlap(obj_a, obj_b):
    "returns result of AABB vs tile collision"
    # get top left and bottom right points of A's box in B's tile space
    a_width = obj_a.right_x - obj_a.left_x
    a_height = obj_a.top_y - obj_a.bottom_y
    # get tiles to iterate over
    b_tile_x_start = (obj_a.left_x - obj_b.left_x) / obj_b.art.quad_width
    b_tile_x_end = b_tile_x_start + a_width / obj_b.art.quad_width
    b_tile_y_start = (obj_b.top_y - obj_a.top_y) / obj_b.art.quad_height
    b_tile_y_end = b_tile_y_start + a_height / obj_b.art.quad_height
    # keep tile checks in-bounds
    def clamp(tile_coord, limit):
        return int(max(0, min(tile_coord, limit)))
    b_tile_x_start = clamp(b_tile_x_start, obj_b.art.width)
    b_tile_x_end = clamp(b_tile_x_end, obj_b.art.width)
    b_tile_y_start = clamp(b_tile_y_start, obj_b.art.height)
    b_tile_y_end = clamp(b_tile_y_end, obj_b.art.height)
    frame = obj_b.renderable.frame
    layer = obj_b.art.layer_names.index(obj_b.col_layer_name)
    hilight = obj_b.art.palette.lightest_index
    #print('checking tiles: X %s-%s, Y %s-%s' % (b_tile_x_start, b_tile_x_end, b_tile_y_start, b_tile_y_end))
    hit_tiles = []
    for x in range(b_tile_x_start, b_tile_x_end+1):
        for y in range(b_tile_y_start, b_tile_y_end+1):
            # non-zero tile = solid?
            tile_char = obj_b.art.get_char_index_at(frame, layer, x, y)
            if tile_char != 0:
                hit_tiles.append((x, y))
    if len(hit_tiles) == 0:
        return None, None
    tile_center_x, tile_center_y = 0, 0
    for tile in hit_tiles:
        obj_b.art.set_color_at(frame, layer, tile[0], tile[1], hilight)
        obj_b.art.set_char_index_at(frame, layer, tile[0], tile[1], 2)
        # return center of last tile checked for now?
        # TODO: this is terrible
        tile_center_x = tile[0] * obj_b.art.quad_width + obj_b.left_x
        tile_center_y = tile[1] * obj_b.art.quad_height + obj_b.top_y
    return tile_center_x, tile_center_y

def get_overlap_loc(obj_a, obj_b):
    """
    returns X,Y coords if objects overlap, None if they don't.
    dispatcher for different collision type check functions, eg BB/tile
    """
    if obj_a.collision_type == CT_AABB and obj_b.collision_type == CT_TILE:
        return get_bb_tile_overlap(obj_a, obj_b)
    # TODO: make objects for more collision types in cronotest
    print('CollisionLord.get_overlap_loc: no handler found for %s + %s' % (obj_a.name, obj_b.name))
    return None, None
