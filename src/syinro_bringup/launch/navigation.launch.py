import os
from ament_index_python.packages import get_package_share_path, get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():

    bringup_pkg = get_package_share_path('syinro_bringup')
    description_pkg = get_package_share_path('my_robot_description')

    urdf_path = os.path.join(str(description_pkg), 'urdf', 'my_robot.urdf.xacro')
    bridge_config = os.path.join(str(bringup_pkg), 'config', 'gazebo_bridge.yaml')
    world_path = os.path.join(str(bringup_pkg), 'worlds', 'obstacles.sdf')
    map_path = os.path.join(str(bringup_pkg), 'maps', 'my_world_map.yaml')
    nav2_params_path = os.path.join(str(bringup_pkg), 'config', 'nav2_params.yaml')
    rviz_path = os.path.join(get_package_share_directory('syinro_bringup'), 'rviz','my_robot_view.rviz')
    # Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    # Robot State Publisher
    rsp = Node(
    package='robot_state_publisher',
    executable='robot_state_publisher',
    parameters=[{
        'robot_description': ParameterValue(
            Command(['xacro ', urdf_path]),
            value_type=str
        ),
        'use_sim_time': True
    }]
)

    # Spawn Robot
    spawn = TimerAction(
        period=5.0,
        actions=[Node(
            package='ros_gz_sim',
            executable='create',
            arguments=['-topic', 'robot_description', '-name', 'my_robot', '-z', '0.1']
        )]
    )

    # Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': str(bridge_config),
            'use_sim_time': True
        }]
    )

    # Nav2 Bringup
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('nav2_bringup'),
                'launch',
                'bringup_launch.py'
            )
        ),
        launch_arguments={
            'map': str(map_path),
            'use_sim_time': 'True',
            'params_file': str(nav2_params_path)
        }.items()
    )

    # RViz with Nav2 default layout
# RViz with Custom Layout
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=[
            '-d', rviz_path
        ],
        parameters=[{'use_sim_time': True}]
    )
    return LaunchDescription([
        gazebo,
        rsp,
        spawn,
        bridge,
        nav2,
        rviz
    ])
