#!/usr/bin/env python3
import rclpy
import time
import threading
import queue
import json
import os
import math
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

class DeliveryDispatcher:
    def __init__(self):
        # 1. Initialize ROS & Nav2
        self.navigator = BasicNavigator()
        
        # 2. Initialize TF2 for tracking robot location (needed for smart-charging)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.navigator)
        
        # 3. Path Setup: Hardcoded absolute path to bypass 'ros2 run' install folders
        self.waypoint_file = '/home/ronak/lucsan_ws/src/syinro_bringup/python_script/waypoints.json'
        self.address_book = {}
        
        # 4. Input Queue for Keyboard Commands
        self.cmd_queue = queue.Queue()
        
        # 5. State Tracking for Charging Lockout
        self.is_charging = False
        
    def load_waypoints(self):
        """Dynamically loads saved waypoints from the local JSON file."""
        if os.path.exists(self.waypoint_file):
            with open(self.waypoint_file, 'r') as f:
                self.address_book = json.load(f)
        else:
            print(f"\n[ERROR] Could not find {self.waypoint_file}!")
            print("Falling back to default 'production' only.")
            self.address_book = {
                "production": {"position": {"x": 0.0, "y": 0.0}, "orientation": {"z": 0.0, "w": 1.0}}
            }

    def get_closest_charging_station(self):
        """Finds all saved chargers and calculates which one is physically closest."""
        chargers = [name for name in self.address_book.keys() if 'charge' in name or 'charging' in name]
        if not chargers:
            return None
            
        try:
            # Ask TF2 where the robot is right now
            trans = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time(), rclpy.duration.Duration(seconds=1.0))
            robot_x = trans.transform.translation.x
            robot_y = trans.transform.translation.y
        except Exception as e:
            print(f"\n[WARNING] Could not find robot location. Defaulting to first charger.")
            return chargers[0]
            
        closest_charger = None
        min_distance = float('inf')
        
        for charger in chargers:
            cx = self.address_book[charger]["position"]["x"]
            cy = self.address_book[charger]["position"]["y"]
            distance = math.hypot(cx - robot_x, cy - robot_y)
            
            if distance < min_distance:
                min_distance = distance
                closest_charger = charger
                
        return closest_charger

    def create_pose(self, name):
        """Converts address book coordinates into a ROS 2 Pose message."""
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.navigator.get_clock().now().to_msg()
        data = self.address_book[name]
        
        pose.pose.position.x = data["position"]["x"]
        pose.pose.position.y = data["position"]["y"]
        pose.pose.position.z = 0.0
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = data["orientation"]["z"]
        pose.pose.orientation.w = data["orientation"]["w"]
        return pose

    def command_listener(self):
        """Background thread to capture keyboard input instantly."""
        while rclpy.ok():
            try:
                user_input = input().strip().lower()
                if user_input:
                    self.cmd_queue.put(user_input)
            except EOFError:
                break

    def process_destinations(self, raw_input):
        """Parses user input, handles smart charging, and adds auto-homing."""
        raw_destinations = [d.strip() for d in raw_input.split(',')]
        processed = []
        
        # 1. Smart Charger Interceptor
        for d in raw_destinations:
            if d in ['charging', 'charge']:
                closest = self.get_closest_charging_station()
                if closest:
                    print(f"\n[INFO] Auto-selected closest charger: '{closest}'")
                    processed.append(closest)
                else:
                    print("\n[WARNING] No charging points exist in waypoints.json! Skipping.")
            else:
                processed.append(d)
                
        # 2. Validate Destinations
        valid_destinations = [d for d in processed if d in self.address_book]
        invalid_dests = [d for d in processed if d not in self.address_book]
        
        if invalid_dests:
            print(f"\n[WARNING] These locations do not exist: {', '.join(invalid_dests)}")
            
        if not valid_destinations:
            return None

        # 3. Auto-Homing Logic
        is_heading_to_charger = any('charge' in d or 'charging' in d for d in valid_destinations)
        if valid_destinations[-1] != 'production' and not is_heading_to_charger:
            if 'production' in self.address_book:
                valid_destinations.append('production')
                print("\n[INFO] 'production' automatically added as the final destination.")
                
        return valid_destinations

    def execute_route(self, route):
        """Drives the robot through the route, handling pauses and waiting."""
        dest_index = 0

        while dest_index < len(route):
            current_dest = route[dest_index]
            self.navigator.goToPose(self.create_pose(current_dest))
            print(f"\n---> Heading to {current_dest}...")

            reroute_triggered = False
            was_paused = False

            # --- NAVIGATION MONITORING LOOP ---
            while not self.navigator.isTaskComplete():
                if not self.cmd_queue.empty():
                    cmd = self.cmd_queue.get()
                    if cmd == 'return':
                        print("\n[INTERRUPT: RETURN] Halting! Rerouting to production.")
                        self.navigator.cancelTask()
                        route = ['production']
                        dest_index = 0
                        reroute_triggered = True
                        break
                    elif cmd == 'cancel':
                        print("\n[INTERRUPT: CANCEL] Aborting route.")
                        self.navigator.cancelTask()
                        return  # Exit routing entirely
                    elif cmd == 'pause':
                        print(f"\n[INTERRUPT: PAUSE] Robot stopped. Type 'resume' to continue.")
                        self.navigator.cancelTask()
                        was_paused = True
                        break
                time.sleep(0.1)

            if reroute_triggered:
                continue

            # --- PAUSE WAITING LOOP ---
            if was_paused:
                while True:
                    if not self.cmd_queue.empty():
                        cmd = self.cmd_queue.get()
                        if cmd == 'resume':
                            print(f"\n[INTERRUPT: RESUME] Restarting path to {current_dest}...")
                            break 
                        elif cmd in ['cancel', 'return']:
                            print(f"\n[INTERRUPT] Action '{cmd}' acknowledged. Aborting current path.")
                            return
                    time.sleep(0.1)
                continue # Restart the loop to go to the current pose again

            # --- ARRIVAL & WAIT LOGIC ---
            result = self.navigator.getResult()
            if result == TaskResult.SUCCEEDED:
                print(f"\n*** Arrived at {current_dest}! ***")
                
                # Check destination type to update charging state
                if 'charge' in current_dest or 'charging' in current_dest:
                    print(f"\nRobot is plugged in and charging at '{current_dest}'.")
                    self.is_charging = True 
                elif current_dest == 'production':
                    print(f"\nRobot is standing by at '{current_dest}'.")
                    self.is_charging = False 
                else:
                    self.handle_wait_timer(15) 
                    self.is_charging = False 
            elif result == TaskResult.FAILED:
                print(f"\n*** Task to {current_dest} failed! Robot got stuck. ***")
                break 

            dest_index += 1

        print("\n" + "*"*50 + "\nROUTE COMPLETE! Ready for next order.\n" + "*"*50)

    def handle_wait_timer(self, seconds):
        """Handles the countdown at tables and listens for skip commands."""
        print(f"Waiting for {seconds} seconds. Type 'ok' to skip.")
        for remaining in range(seconds, 0, -1):
            if not self.cmd_queue.empty():
                cmd = self.cmd_queue.get()
                if cmd == 'ok':
                    print("\n[INTERRUPT: OK] Wait skipped! Proceeding.")
                    return
                elif cmd in ['cancel', 'return']:
                    print(f"\n[INTERRUPT] Timer aborted by '{cmd}'.")
                    return
            print(f"\rCountdown: {remaining} seconds remaining... ", end="", flush=True)
            time.sleep(1)
        print("\nTimer finished!")

    def run(self):
        """The main UI and dispatch loop."""
        print("Waiting for Nav2 to boot up...")
        self.navigator.waitUntilNav2Active()
        print("Nav2 is ready!\n")

        # Start listening to the keyboard
        threading.Thread(target=self.command_listener, daemon=True).start()

        while rclpy.ok():
            self.load_waypoints() # Reloads waypoints fresh every cycle
            
            # --- MENU DISPLAY LOGIC ---
            if self.is_charging:
                print("\n" + "="*50)
                print("         ROBOT IS CHARGING")
                print("="*50)
                print("The robot must return to the kitchen to load food before taking new orders.")
                print("Type 'production' or 'return' to recall the robot > ")
            else:
                print("\n" + "="*50)
                print("         DELIVERY DISPATCH SYSTEM")
                print("="*50)
                # Display only the first 8 points so it doesn't clutter the screen
                points = list(self.address_book.keys())
                display_points = ', '.join(points[:8])
                print(f"Mapped points: {display_points} ... ({len(points)} total locations)")
                print("Live Commands: 'pause', 'resume', 'return', 'cancel', 'ok', 'charge'")
                print("Type destinations separated by commas > ")

            # Wait for user to type something
            while self.cmd_queue.empty():
                time.sleep(0.1)

            user_input = self.cmd_queue.get()

            if user_input in ['quit', 'exit']:
                print("Shutting down...")
                break
                
            # --- INPUT HANDLING LOGIC ---
            if self.is_charging:
                if user_input in ['return', 'production']:
                    route = ['production']
                    self.is_charging = False # Unlock the system as it heads back
                else:
                    print("\n[ERROR] Command locked. Type 'production' or 'return' to recall the robot.")
                    continue
            else:
                if user_input in ['cancel', 'pause', 'resume', 'ok']:
                    print(f"Cannot '{user_input}' right now. Robot is idle.")
                    continue
                    
                if user_input == 'return':
                    route = ['production']
                else:
                    route = self.process_destinations(user_input)

            # Dispatch the robot if a valid route exists
            if route:
                self.execute_route(route)

def main():
    rclpy.init()
    dispatcher = DeliveryDispatcher()
    try:
        dispatcher.run()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()