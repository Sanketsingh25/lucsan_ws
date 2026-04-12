import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_description = get_package_share_directory('my_robot_description')
    pkg_bringup = get_package_share_directory('syinro_bringup') 
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    pkg_slam_toolbox = get_package_share_directory('slam_toolbox')
    

    xacro_file = os.path.join(pkg_description, 'urdf', 'my_robot.urdf.xacro')
    bridge_params = os.path.join(pkg_bringup, 'config', 'gazebo_bridge.yaml')
    world_path = os.path.join(pkg_bringup, 'worlds', 'obstacles.sdf')
    
    # 1. Gazebo Sim with the obstacle world
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    # 2. Process Xacro & Publish Robot Description
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str),
            'use_sim_time': True
        }]
    )

    # 3. Spawn the robot into Gazebo (Delayed by 5 seconds to let Gazebo load)
    spawn_entity = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='ros_gz_sim',
                executable='create',
                output='screen',
                arguments=[
                    '-topic', 'robot_description',
                    '-name', 'my_robot',
                    '-z', '0.1' 
                ]
            )
        ]
    )

    # 4. Start the Bridge for Sensors and cmd_vel
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': str(bridge_params),
            'use_sim_time': True
        }],
        output='screen'
    )

    # 5. SLAM Toolbox (Asynchronous Online Mapping)
    start_slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_slam_toolbox, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={'use_sim_time': 'True'}.items()
    )

    # 6. Start RViz 2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )
    # Start the EKF node to fuse wheel odometry and IMU for perfect mapping
 
    return LaunchDescription([
        gazebo,
        robot_state_publisher_node,
        spawn_entity,
        bridge_node,
        start_slam_toolbox,
        rviz_node
       
    ])