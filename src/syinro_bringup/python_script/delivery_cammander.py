#!/usr/bin/env python3
import rclpy
import time
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

def main():
    rclpy.init()
    navigator = BasicNavigator()

    print("Waiting for Nav2 to boot up...")
    navigator.waitUntilNav2Active()
    print("Nav2 is ready!\n")

    # --- THE INFINITE LOOP STARTS HERE ---
    while True:
        print("\n" + "="*50)
        print("         DELIVERY DISPATCH SYSTEM")
        print("="*50)
        print("Available points: 'table 1', 'table 2', 'production',charging")
        print("Type 'quit' or 'exit' to shut down.")
        
        user_input = input("\nWhere should the robot go? (separate multiple with commas) > ")

        if user_input.strip().lower() in ['quit', 'exit']:
            print("\nShutting down the dispatcher. Goodbye!")
            break

        raw_destinations = [d.strip().lower() for d in user_input.split(',')]
        valid_destinations = [d for d in raw_destinations if d in ADDRESS_BOOK]

        if not valid_destinations:
            print("No valid destinations recognized. Please try again.")
            continue 

        print(f"\nDispatching robot through route: {', '.join(valid_destinations)}...")
        
        # We loop through the names, but we DO NOT create the poses yet!
        for current_dest_name in valid_destinations:
            
            # 1. FIX: Generate the pose right before driving so the timestamp is fresh!
            current_pose = create_pose(navigator, current_dest_name)

            print(f"\n---> Heading to {current_dest_name}...")
            navigator.goToPose(current_pose)

            # 2. FIX: Add a 0.1s sleep so we don't crush your CPU
            while not navigator.isTaskComplete():
                time.sleep(0.1)

            result = navigator.getResult()
            if result == TaskResult.SUCCEEDED:
                print(f"\n*** Arrived at {current_dest_name}! ***")
                
                wait_time_seconds = 15  
                print(f"Waiting for {wait_time_seconds} seconds ")
                for remaining in range(wait_time_seconds, 0, -1):
                    print(f"\rCountdown: {remaining} seconds remaining... ", end="", flush=True)
                    time.sleep(1)
                print("\nTimer finished!")

            elif result == TaskResult.CANCELED:
                print(f"\n*** Task to {current_dest_name} canceled. Stopping route. ***")
                break 
            elif result == TaskResult.FAILED:
                print(f"\n*** Task to {current_dest_name} failed! Robot got stuck. ***")
                break 

        print("\n" + "*"*50)
        print("ALL DELIVERIES FOR THIS ROUTE COMPLETE! Ready for the next order.")
        print("*"*50)

    rclpy.shutdown()

if __name__ == '__main__':
    main()