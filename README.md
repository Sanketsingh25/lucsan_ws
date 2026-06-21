
> A full-stack ROS2 Humble simulation workspace for an autonomous indoor mobile robot — featuring Nav2 navigation, AMCL localization, custom sensor integration, and autonomous startup behavior.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Demo](#-demo)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Key Technical Decisions](#-key-technical-decisions)
- [Author](#-author)

---

## 🧭 Overview

**lucsan_ws** is a ROS2 Humble workspace that simulates and drives an autonomous indoor mobile robot. The stack covers everything from sensor fusion and localization to full autonomous navigation — designed with real-world deployment in restaurants, offices, and hospitals in mind.

The project is tightly coupled with the **Yoyo** food delivery robot, where the same Nav2 stack runs in production on a real Reeman chassis. This simulation workspace mirrors that architecture, making it easy to tune, test, and validate behavior before deploying to hardware.

---

## 🎬 Demo
https://www.linkedin.com/posts/sanket-singh-b73254311_roboticsengineering-ros-autonomousvehicles-activity-7444435685434118144-xY1F?utm_source=share&utm_medium=member_android&rcm=ACoAAE88nocBCJ3q9qHaaxesoTRyz8kQhX72KM0

https://www.linkedin.com/posts/sanket-singh-b73254311_robotics-autonomousrobots-lidar-activity-7469266228042407936-NIU_?utm_source=share&utm_medium=member_android&rcm=ACoAAE88nocBCJ3q9qHaaxesoTRyz8kQhX72KM0

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      ROS2 Humble                        │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌────────────────────┐  │
│  │  Sensors  │──▶│  Nav2    │──▶│  Robot Controller  │  │
│  │ LiDAR    │   │  Stack   │   │  (cmd_vel)         │  │
│  │ Depth Cam│   │          │   └────────────────────┘  │
│  │ IMU      │   │  AMCL    │                            │
│  └──────────┘   │  Costmap │   ┌────────────────────┐  │
│                 │  Planner │   │  Auto Localizer     │  │
│                 │  BT Nav  │──▶│  (startup pose)    │  │
│                 └──────────┘   └────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```


---

## ✨ Features

| Feature | Details |
|---|---|
| 🗺️ **Autonomous Navigation** | Nav2 with A* global planner + DWB local planner |
| 📍 **AMCL Localization** | Adaptive Monte Carlo with kidnap recovery |
| 🧱 **Obstacle Avoidance** | Persistent costmap with depth camera + LiDAR fusion |
| 🔄 **Auto Startup Localization** | Saved pose → AMCL convergence → global relocalization fallback |
| 🚫 **Safe Recovery** | Spin-only recovery (no backup — rear sensor blind zone aware) |
| 🛞 **Sensor Fusion** | Dual depth cameras + LiDAR + WT901 IMU |
| ⚙️ **Tuned Nav Params** | Production-validated `nav2_params.yaml` for real indoor environments |

---

## 🛠️ Tech Stack

- **Middleware:** ROS2 Humble
- **Navigation:** Nav2 (AMCL, BT Navigator, Controller Server, Planner Server)
- **Simulation:** Gazebo Classic
- **Languages:** Python (96%), CMake
- **Sensors (real hardware mirrored in sim):**
  - LTME-02A LiDAR (Ethernet)
  - MetaSense615U Depth Cameras × 2
  - WT901 IMU (custom binary protocol driver)


---

## 📁 Package Structure

```
lucsan_ws/
└── src/
    ├── <robot_description>/     # URDF / xacro robot model
    └── <bringup>/               # RVIZ,config,launch,python_script,world,map
```


## 🚀 Getting Started

### Prerequisites

- Ubuntu 22.04
- ROS2 Humble (`ros-humble-desktop`)
- Nav2 (`sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup`)
- Gazebo ignition

### Build

```bash
cd lucsan_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Launch Simulation

```bash
# For mapping
ros2 launch syinro my_robot_mapping.launch.py

# For autonomus navigation
ros2 launch syinro navigation.launch.py use_sim_time:=True
```
---

## 👤 Author

**Sanket Singh**
Robotics Engineer | ROS2 · Nav2 · Sensor Fusion · Autonomous Systems

- 🔗 [GitHub](https://github.com/Sanketsingh25)
- 📧 sanketspsingh@gmail.com
