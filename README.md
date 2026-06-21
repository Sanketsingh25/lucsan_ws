
> A full-stack ROS2 Humble simulation workspace for an autonomous indoor mobile robot — featuring Nav2 navigation, AMCL localization, custom sensor integration, and autonomous startup behavior.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Demo](#-demo)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Package Structure](#-package-structure)
- [Getting Started](#-getting-started)
- [Key Technical Decisions](#-key-technical-decisions)
- [Author](#-author)

---

## 🧭 Overview

**lucsan_ws** is a ROS2 Humble workspace that simulates and drives an autonomous indoor mobile robot. The stack covers everything from sensor fusion and localization to full autonomous navigation — designed with real-world deployment in restaurants, offices, and hospitals in mind.

The project is tightly coupled with the **Yoyo** food delivery robot, where the same Nav2 stack runs in production on a real Reeman chassis. This simulation workspace mirrors that architecture, making it easy to tune, test, and validate behavior before deploying to hardware.

---

## 🎬 Demo

> *(Add a GIF or video link here — e.g., Gazebo simulation, RViz navigation, or a screen recording of the robot autonomously navigating)*

```
📹 [Simulation Demo — coming soon]
📸 Screenshots of RViz + costmaps — see /docs/images/
```

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

The architecture bridges a ROS1 Docker-based chassis driver to the ROS2 navigation stack via a **custom Python WebSocket bridge** (`rosbridge_suite` + `roslibpy`), enabling real hardware reuse of the simulation stack.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🗺️ **Autonomous Navigation** | Nav2 with A* global planner + DWB local planner |
| 📍 **AMCL Localization** | Adaptive Monte Carlo with kidnap recovery |
| 🧱 **Obstacle Avoidance** | Persistent costmap with depth camera + LiDAR fusion |
| 🔄 **Auto Startup Localization** | Saved pose → AMCL convergence → global relocalization fallback |
| 🚫 **Safe Recovery** | Spin-only recovery (no backup — rear sensor blind zone aware) |
| 🌉 **ROS1/ROS2 Bridge** | Custom WebSocket bridge for Reeman chassis driver interop |
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
- **Bridge:** `rosbridge_suite` + `roslibpy` WebSocket bridge
- **Containerization:** Docker (Reeman chassis driver isolation)

---

## 📁 Package Structure

```
lucsan_ws/
└── src/
    ├── <robot_description>/     # URDF / xacro robot model
    ├── <navigation>/            # Nav2 config, launch files, BT XMLs
    ├── <localization>/          # AMCL params, auto_localizer.py
    ├── <sensor_drivers>/        # Custom IMU driver, laser_time_fixer
    └── <bringup>/               # start_everything.sh, launch orchestration
```

> *Note: Package names are illustrative — see `src/` for actual package names.*

---

## 🚀 Getting Started

### Prerequisites

- Ubuntu 22.04
- ROS2 Humble (`ros-humble-desktop`)
- Nav2 (`sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup`)
- Gazebo Classic

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


## 🧠 Key Technical Decisions

### 1. Persistent Obstacle Marking
Camera sources use `clearing: False` + `observation_persistence` to ensure chair caster wheels and low obstacles are **never erased** from the costmap during navigation — solving a real blind-zone collision problem.

### 2. No Backup Recovery
All backward recovery behaviors are **disabled**. The robot has a rear sensor blind zone, so reversing without perception is unsafe. Recovery is spin-in-place only.

### 3. Auto Localization Pipeline
On startup, the robot: (1) loads the last saved pose, (2) waits for AMCL particle convergence, and (3) falls back to a slow global spin for relocalization — eliminating the need for manual `2D Pose Estimate` at deployment.

---

## 👤 Author

**Sanket Singh**
Robotics Engineer | ROS2 · Nav2 · Sensor Fusion · Autonomous Systems

- 🔗 [GitHub](https://github.com/Sanketsingh25)
- 📧 sanketspsingh@gmail.com
