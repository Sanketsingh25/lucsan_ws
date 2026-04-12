#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import json
import os
import threading
import sys
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from visualization_msgs.msg import Marker, MarkerArray  # <-- Required for drawing on map

# --- ABSOLUTE PATH FIX ---
WAYPOINT_FILE = os.path.expanduser('~/lucsan_ws/src/syinro_bringup/python_script/waypoints.json')
# -------------------------

class WaypointMapper(Node):
    def __init__(self):
        super().__init__('waypoint_mapper')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Publisher to send text markers to RViz
        self.marker_pub = self.create_publisher(MarkerArray, 'waypoint_markers', 10)
        
        # Timer to refresh markers every 2 seconds
        self.timer = self.create_timer(2.0, self.publish_markers)
        
    def save_location(self, name):
        try:
            trans = self.tf_buffer.lookup_transform(
                'map', 'base_link', rclpy.time.Time(), rclpy.duration.Duration(seconds=1.0)
            )
            
            address_book = {}
            if os.path.exists(WAYPOINT_FILE):
                with open(WAYPOINT_FILE, 'r') as f:
                    address_book = json.load(f)
            
            address_book[name] = {
                "position": {
                    "x": round(trans.transform.translation.x, 4), 
                    "y": round(trans.transform.translation.y, 4)
                },
                "orientation": {
                    "z": round(trans.transform.rotation.z, 4), 
                    "w": round(trans.transform.rotation.w, 4)
                }
            }
            
            os.makedirs(os.path.dirname(WAYPOINT_FILE), exist_ok=True)
            
            with open(WAYPOINT_FILE, 'w') as f:
                json.dump(address_book, f, indent=4)
                
            print(f"\n[SUCCESS] Saved '{name}' to {WAYPOINT_FILE}!")
            
            # Instantly update map graphics
            self.publish_markers()
            
        except Exception as e:
            print(f"\n[ERROR] Could not find the robot on the map. Is Nav2/AMCL running? Details: {e}")

    def publish_markers(self):
        if not os.path.exists(WAYPOINT_FILE):
            return 
            
        try:
            with open(WAYPOINT_FILE, 'r') as f:
                address_book = json.load(f)
        except json.JSONDecodeError:
            return 
            
        marker_array = MarkerArray()
        m_id = 0
        
        for name, coords in address_book.items():
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'waypoints'
            marker.id = m_id
            
            # Floating text
            marker.type = Marker.TEXT_VIEW_FACING
            marker.action = Marker.ADD
            
            # Position it right where the robot was
            marker.pose.position.x = coords['position']['x']
            marker.pose.position.y = coords['position']['y']
            marker.pose.position.z = 0.5  # Float half a meter off the ground
            
            marker.scale.z = 0.5  # Size of the text
            
            # Bright Green text
            marker.color.a = 1.0  
            marker.color.r = 0.0  
            marker.color.g = 1.0  
            marker.color.b = 0.0  
            
            marker.text = name
            
            marker_array.markers.append(marker)
            m_id += 1
            
        self.marker_pub.publish(marker_array)

def input_loop(mapper_node):
    print("="*50)
    print("             ROBOT MAPPING TOOL")
    print("="*50)
    print("Drive the robot to the desired location manually.")
    
    while rclpy.ok():
        try:
            name = input("\nEnter location name to save (e.g., 'table 1') or 'quit' to exit > ").strip().lower()
            if name in ['quit', 'exit']:
                print("\nShutting down mapping tool...")
                rclpy.shutdown()
                sys.exit(0)
            if name:
                mapper_node.save_location(name)
        except (EOFError, KeyboardInterrupt):
            rclpy.shutdown()
            sys.exit(0)

def main():
    rclpy.init()
    mapper = WaypointMapper()
    
    thread = threading.Thread(target=input_loop, args=(mapper,), daemon=True)
    thread.start()
    
    try:
        rclpy.spin(mapper)
    except KeyboardInterrupt:
        pass
        
    if rclpy.ok():
        mapper.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()