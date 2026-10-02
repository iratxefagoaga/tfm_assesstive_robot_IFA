#include <chrono>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>

#include "ament_index_cpp/get_package_share_directory.hpp"
#include "behaviortree_cpp/action_node.h"
#include "behaviortree_cpp/bt_factory.h"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "wheelchair_assistive_bt/common_experiment_logging.hpp"


// Isolate N0's BT type names when linking both production row builders in one test.
namespace n0_logging_reference { using namespace wheelchair_assistive_bt; }
#define WHEELCHAIR_ASSISTIVE_BT_N0_LOGGING_TEST
#define wheelchair_assistive_bt n0_logging_reference
#include "../src/assistive_bt_orchestrator.cpp"
#undef wheelchair_assistive_bt

wheelchair_assistive_bt::ResultRow n0_reference_row(
  const BT::Blackboard::Ptr & bb, const wheelchair_assistive_bt::NavigationMetrics & metrics)
{
  return n0_logging_reference::n0_result_row(bb, metrics);
}
