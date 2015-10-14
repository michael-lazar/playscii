{
 "current_room": "starting",
 "objects": [
  {
   "alpha": 1.0,
   "animating": false,
   "art_off_pct_x": 0.5,
   "art_off_pct_y": 0.5,
   "art_src": "bg2",
   "class_name": "StaticTileBG",
   "facing": 3,
   "locked": false,
   "name": "otherBG",
   "scale_x": 1.0,
   "scale_y": 1.0,
   "state": "stand",
   "visible": true,
   "x": -44.0,
   "y": 4.0,
   "y_sort": false,
   "z": 0.0
  },
  {
   "class_name": "LocationMarker",
   "locked": false,
   "name": "room1cam",
   "visible": true,
   "x": -4.0,
   "y": 4.0,
   "z": 16.0
  },
  {
   "alpha": 1.0,
   "animating": false,
   "art_off_pct_x": 0.5,
   "art_off_pct_y": 0.5,
   "art_src": "bg1",
   "class_name": "StaticTileBG",
   "facing": 2,
   "locked": false,
   "name": "startBG",
   "scale_x": 1.0,
   "scale_y": 1.0,
   "state": "stand",
   "visible": true,
   "x": -3.908042957591931,
   "y": 3.7514192945110874,
   "y_sort": false,
   "z": 0.0
  },
  {
   "class_name": "LocationMarker",
   "locked": false,
   "name": "roomScam",
   "visible": true,
   "x": -16.313843601051023,
   "y": -18.062721956618176,
   "z": 8.989488752238989
  },
  {
   "alpha": 1.0,
   "animating": false,
   "art_off_pct_x": 0.5,
   "art_off_pct_y": 0.5,
   "art_src": "player",
   "class_name": "MazePlayer",
   "facing": 0,
   "locked": false,
   "name": "MazePlayer_7f81aab05b00",
   "scale_x": 1.0,
   "scale_y": 1.0,
   "state": "stand",
   "visible": true,
   "x": -15.059266360438828,
   "y": 9.354556506226709,
   "y_sort": false,
   "z": 0.1
  },
  {
   "class_name": "LocationMarker",
   "locked": false,
   "name": "room2cam",
   "visible": true,
   "x": -44.10279257082698,
   "y": 4.0,
   "z": 17.070995359986807
  },
  {
   "class_name": "ObjectSpawner",
   "destroy_on_room_exit": false,
   "locked": false,
   "name": "ObjectSpawner_7f219b3e0b38",
   "spawn_class_name": "MazeCritter",
   "spawn_obj_name": "critter1",
   "times_to_fire": 1,
   "visible": false,
   "x": -44.93263264777972,
   "y": 9.808880365551065,
   "z": 0.0
  },
  {
   "alpha": 1.0,
   "animating": false,
   "art_off_pct_x": 0.5,
   "art_off_pct_y": 0.5,
   "art_src": "bg3",
   "class_name": "StaticTileBG",
   "facing": 2,
   "locked": true,
   "name": "southBG",
   "scale_x": 1.0,
   "scale_y": 1.0,
   "state": "stand",
   "visible": true,
   "x": -16.0,
   "y": -18.5,
   "y_sort": false,
   "z": 0.0
  },
  {
   "bg_color_a": 0,
   "bg_color_b": 0,
   "bg_color_g": 0,
   "bg_color_r": 0,
   "camera_x": -4.0,
   "camera_y": 4.0,
   "camera_z": 16.0,
   "class_name": "WorldPropertiesObject",
   "collision_enabled": true,
   "draw_hud": true,
   "globals_object_class_name": "WorldGlobalsObject",
   "gravity_x": 0.0,
   "gravity_y": 0.0,
   "gravity_z": 0.0,
   "hud_class_name": "GameHUD",
   "object_grid_snap": true,
   "player_camera_lock": false,
   "show_bounds_all": false,
   "show_collision_all": false,
   "show_origin_all": false
  }
 ],
 "rooms": [
  {
   "bottom_edge_warp_dest_name": "",
   "camera_marker_name": "roomScam",
   "class_name": "GameRoom",
   "left_edge_warp_dest_name": "",
   "name": "southroom",
   "objects": [
    "roomScam",
    "southBG"
   ],
   "right_edge_warp_dest_name": "",
   "top_edge_warp_dest_name": "starting",
   "warp_edge_bounds_obj_name": "southBG"
  },
  {
   "bottom_edge_warp_dest_name": "southroom",
   "camera_marker_name": "room1cam",
   "class_name": "GameRoom",
   "left_edge_warp_dest_name": "tha_next",
   "name": "starting",
   "objects": [
    "startBG"
   ],
   "right_edge_warp_dest_name": "",
   "top_edge_warp_dest_name": "",
   "warp_edge_bounds_obj_name": "startBG"
  },
  {
   "bottom_edge_warp_dest_name": "",
   "camera_marker_name": "room2cam",
   "class_name": "GameRoom",
   "left_edge_warp_dest_name": "",
   "name": "tha_next",
   "objects": [
    "otherBG",
    "ObjectSpawner_7f219b3e0b38"
   ],
   "right_edge_warp_dest_name": "starting",
   "top_edge_warp_dest_name": "",
   "warp_edge_bounds_obj_name": "otherBG"
  }
 ]
}