cmake_minimum_required(VERSION 3.8)
project(wheelchair_assistive_bt)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(action_msgs REQUIRED)
find_package(behaviortree_cpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(lifecycle_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(wheelchair_interfaces REQUIRED)

add_executable(assistive_bt_orchestrator src/assistive_bt_orchestrator.cpp)
target_include_directories(assistive_bt_orchestrator PRIVATE include)
ament_target_dependencies(assistive_bt_orchestrator
  ament_index_cpp action_msgs behaviortree_cpp geometry_msgs lifecycle_msgs
  nav2_msgs nav_msgs rclcpp rclcpp_action wheelchair_interfaces)

add_executable(memory_observation_bt_orchestrator src/memory_observation_orchestrator.cpp)
target_include_directories(memory_observation_bt_orchestrator PRIVATE include)
ament_target_dependencies(memory_observation_bt_orchestrator
  ament_index_cpp action_msgs behaviortree_cpp geometry_msgs lifecycle_msgs
  nav2_msgs nav_msgs rclcpp rclcpp_action wheelchair_interfaces)

install(TARGETS assistive_bt_orchestrator memory_observation_bt_orchestrator DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY behavior_trees launch DESTINATION share/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
install(PROGRAMS scripts/wait_for_smoke_ready.py scripts/managed_memory_process.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  foreach(mode n0 n1)
    ament_add_gtest(test_readiness_${mode} test/test_readiness_${mode}.cpp)
    target_include_directories(test_readiness_${mode} PRIVATE include)
    ament_target_dependencies(test_readiness_${mode}
      ament_index_cpp action_msgs behaviortree_cpp geometry_msgs lifecycle_msgs
      nav2_msgs nav_msgs rclcpp rclcpp_action wheelchair_interfaces)
  endforeach()

  add_test(NAME test_smoke_lifecycle
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/test/test_smoke_lifecycle.py)

  ament_add_gtest(test_n1_logging test/test_n1_logging.cpp test/n0_logging_reference.cpp)
  target_include_directories(test_n1_logging PRIVATE include)
  ament_target_dependencies(test_n1_logging
    ament_index_cpp action_msgs behaviortree_cpp geometry_msgs lifecycle_msgs
    nav2_msgs nav_msgs rclcpp rclcpp_action wheelchair_interfaces)

  ament_add_gtest(test_n0_logging test/test_n0_logging.cpp)
  target_include_directories(test_n0_logging PRIVATE include)
  ament_target_dependencies(test_n0_logging
    ament_index_cpp action_msgs behaviortree_cpp geometry_msgs lifecycle_msgs
    nav2_msgs nav_msgs rclcpp rclcpp_action)

  ament_add_gtest(test_resolve_strategy_waypoint test/test_resolve_strategy_waypoint.cpp)
  target_include_directories(test_resolve_strategy_waypoint PRIVATE include)
  ament_target_dependencies(test_resolve_strategy_waypoint
    ament_index_cpp action_msgs behaviortree_cpp geometry_msgs lifecycle_msgs
    nav2_msgs nav_msgs rclcpp rclcpp_action wheelchair_interfaces)
endif()

ament_package()
