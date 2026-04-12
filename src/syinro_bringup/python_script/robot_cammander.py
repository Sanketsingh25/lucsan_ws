#!/usr/bin/env python3
import rclpy
import time
import threading
import queue
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

# Your Robot's Address Book
ADDRESS_BOOK = {
    "table 1": {
        "position": {"x": 1.3027, "y": 6.6629},
        "orientation": {"z": -0.8869, "w": 0.4617}
    },
    "table 2": {
        "position": {"x": 1.3445, "y": -5.8082},
        "orientation": {"z": -0.9870, "w": 0.1604}
    },
    "production": {
        "position": {"x": -0.1183, "y": -0.1523},
        "orientation": {"z": 0.0878, "w": 0.9961}
    },
    "charging": {
        "position": {"x": 2.0901, "y": -8.2559},
        "orientation": {"z": 0.8340, "w": 0.5517}
    }
}

def create_pose(navigator, name):
    """Converts the address book dictionary into a ROS 2 Pose message"""
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = ADDRESS_BOOK[name]["position"]["x"]
    pose.pose.position.y = ADDRESS_BOOK[name]["position"]["y"]
    pose.pose.position.z = 0.0
    pose.pose.orientation.x = 0.0
    pose.pose.orientation.y = 0.0
    pose.pose.orientation.z = ADDRESS_BOOK[name]["orientation"]["z"]
    pose.pose.orientation.w = ADDRESS_BOOK[name]["orientation"]["w"]
    return pose

def command_listener(cmd_queue):
    """Background thread that listens to the keyboard without blocking the robot"""
    while True:
        try:
            user_input = input().strip().lower()
            if user_input:
                cmd_queue.put(user_input)
        except EOFError:
            break

def main():
    rclpy.init()
    navigator = BasicNavigator()

    print("Waiting for Nav2 to boot up...")
    navigator.waitUntilNav2Active()
    print("Nav2 is ready!\n")

    cmd_queue = queue.Queue()
    input_thread = threading.Thread(target=command_listener, args=(cmd_queue,), daemon=True)
    input_thread.start()

    # --- THE INFINITE LOOP STARTS HERE ---
    while True:
        print("\n" + "="*50)
        print("         DELIVERY DISPATCH SYSTEM")
        print("="*50)
        print("Available points: 'table 1', 'table 2', 'production', 'charging'")
        print("Live Commands: 'pause', 'resume', 'return' (to production), 'cancel' (new input)")
        print("Type destinations separated by commas to begin > ")

        while cmd_queue.empty():
            time.sleep(0.1)

        user_input = cmd_queue.get()

        if user_input in ['quit', 'exit']:
            print("\nShutting down the dispatcher. Goodbye!")
            break
            
        if user_input in ['cancel', 'pause', 'resume', 'return']:
            if user_input == 'return':
                print("\nInitiating return. Routing directly to production.")
                valid_destinations = ['production']
            elif user_input == 'cancel':
                print("\nRobot is already idle. Waiting for new destinations.")
                continue
            else:
                print(f"\nCannot '{user_input}' right now. The robot is currently idle.")
                continue
        else:
            raw_destinations = [d.strip() for d in user_input.split(',')]
            valid_destinations = [d for d in raw_destinations if d in ADDRESS_BOOK]

        if not valid_destinations:
            print("No valid destinations recognized. Please try again.")
            continue 

        print(f"\nDispatching robot through route: {', '.join(valid_destinations)}...")
        
        dest_index = 0
        abort_route = False # This flag tells the script to ask for fresh input

        while dest_index < len(valid_destinations):
            current_dest_name = valid_destinations[dest_index]
            current_pose = create_pose(navigator, current_dest_name)

            print(f"\n---> Heading to {current_dest_name}...")
            navigator.goToPose(current_pose)

            reroute_triggered = False
            was_paused = False

            # --- THE NAVIGATION MONITORING LOOP ---
            while not navigator.isTaskComplete():
                if not cmd_queue.empty():
                    live_cmd = cmd_queue.get()

                    if live_cmd == 'return':
                        print("\n[INTERRUPT: RETURN] Halting current route. Rerouting to production!")
                        navigator.cancelTask()
                        valid_destinations = ['production']
                        dest_index = 0
                        reroute_triggered = True
                        break
                        
                    elif live_cmd == 'cancel':
                        print("\n[INTERRUPT: CANCEL] Aborting entire route. Waiting for fresh input.")
                        navigator.cancelTask()
                        abort_route = True
                        break

                    elif live_cmd == 'pause':
                        print(f"\n[INTERRUPT: PAUSE] Stopping robot. Waiting for 'resume' to continue to {current_dest_name}...")
                        navigator.cancelTask() 
                        was_paused = True
                        break
                        
                    elif live_cmd in ['quit', 'exit']:
                        navigator.cancelTask()
                        rclpy.shutdown()
                        return

                time.sleep(0.1)

            # If user typed 'cancel', break completely out of the delivery loop
            if abort_route:
                break

            # If user typed 'return', jump to the top of the route loop to head to production
            if reroute_triggered:
                continue

            # --- THE PAUSE WAITING LOOP ---
            if was_paused:
                while True:
                    if not cmd_queue.empty():
                        resume_cmd = cmd_queue.get()
                        if resume_cmd == 'resume':
                            print(f"\n[INTERRUPT: RESUME] Restarting path to {current_dest_name}...")
                            break 
                        elif resume_cmd == 'return':
                            print("\n[INTERRUPT: RETURN] Halting current route. Rerouting to production!")
                            valid_destinations = ['production']
                            dest_index = 0
                            reroute_triggered = True
                            break
                        elif resume_cmd == 'cancel':
                            print("\n[INTERRUPT: CANCEL] Aborting entire route. Waiting for fresh input.")
                            abort_route = True
                            break
                    time.sleep(0.1)
                
                if abort_route:
                    break
                if reroute_triggered:
                    continue
                else:
                    # If they resumed, jump to top of route loop WITHOUT incrementing dest_index. 
                    continue

            # --- DESTINATION ARRIVAL LOGIC ---
            result = navigator.getResult()
            if result == TaskResult.SUCCEEDED:
                print(f"\n*** Arrived at {current_dest_name}! ***")
                
                wait_time_seconds = 15  
                print(f"Waiting for {wait_time_seconds} seconds ")
                
                for remaining in range(wait_time_seconds, 0, -1):
                    if not cmd_queue.empty():
                        wait_cmd = cmd_queue.get()
                        if wait_cmd == 'return':
                            print("\n[INTERRUPT: RETURN] Wait interrupted! Heading to production.")
                            valid_destinations = ['production']
                            dest_index = 0
                            reroute_triggered = True
                            break
                        elif wait_cmd == 'cancel':
                            print("\n[INTERRUPT: CANCEL] Wait interrupted! Aborting route.")
                            abort_route = True
                            break
                        elif wait_cmd == 'pause':
                            print("\n[INFO] Robot is already stopped at the destination.")
                            
                    print(f"\rCountdown: {remaining} seconds remaining... ", end="", flush=True)
                    time.sleep(1)
                print("\nTimer finished!")

            elif result == TaskResult.CANCELED:
                # Catch-all for cancellations not handled by our loops
                pass 
            elif result == TaskResult.FAILED:
                print(f"\n*** Task to {current_dest_name} failed! Robot got stuck. ***")
                break 
            
            if abort_route:
                break
            if reroute_triggered:
                continue

            # Only move to the next table if we completed the current one successfully
            dest_index += 1

        if not abort_route:
            print("\n" + "*"*50)
            print("ALL DELIVERIES FOR THIS ROUTE COMPLETE! Ready for the next order.")
            print("*"*50)

    rclpy.shutdown()

if __name__ == '__main__':
    main()