cmake_minimum_required(VERSION 3.8)
project(wheelchair_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    config
  DESTINATION
    share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/scan_frame_fixer.py
    scripts/baseline_runner.py
  DESTINATION
    lib/${PROJECT_NAME}
)

ament_package()