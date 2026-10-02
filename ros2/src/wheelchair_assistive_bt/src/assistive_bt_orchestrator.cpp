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
#include "wheelchair_assistive_bt/nav2_readiness.hpp"

namespace wheelchair_assistive_bt
{
using NavigateToPose = nav2_msgs::action::NavigateToPose;
using GoalHandleNavigateToPose = rclcpp_action::ClientGoalHandle<NavigateToPose>;
using GetState = lifecycle_msgs::srv::GetState;
using namespace std::chrono_literals;

struct ExecutionContext
{
  rclcpp::Node * node{nullptr};
  std::shared_ptr<NavigationMetrics> metrics;
  std::shared_ptr<Nav2ReadinessCheck> readiness;
  rclcpp_action::Client<NavigateToPose>::SharedPtr navigate_client;
  std::chrono::milliseconds wait_for_nav2_timeout{60000};
  std::chrono::milliseconds navigation_timeout{120000};
};

class ContextNode
{
protected:
  explicit ContextNode(const BT::NodeConfiguration & config) : config_(config)
  {
    if (!config_.blackboard->get("execution_context", context_)) {
      throw BT::RuntimeError("Behavior Tree blackboard is missing execution_context");
    }
  }

  void set_failure(const std::string & stage, const std::string & reason)
  {
    config_.blackboard->set("failure_stage", stage);
    config_.blackboard->set("failure_reason", reason);
    config_.blackboard->set("success", false);
  }

  void set_nav_result(const std::string & result)
  {
    config_.blackboard->set("final_goal_nav2_result", result);
    config_.blackboard->set("nav2_result", result);
    config_.blackboard->set("success", result == "SUCCEEDED");
  }

  BT::NodeStatus readiness_failure(const std::string & reason)
  {
    config_.blackboard->set("final_goal_nav2_result", std::string("NOT_SENT"));
    config_.blackboard->set("nav2_result", std::string("NOT_SENT"));
    set_failure("readiness", reason);
    return BT::NodeStatus::FAILURE;
  }

  std::shared_ptr<ExecutionContext> context_;
  BT::NodeConfiguration config_;
};

class WaitForNav2Active : public BT::StatefulActionNode, private ContextNode
{
public:
  WaitForNav2Active(const std::string & name, const BT::NodeConfiguration & config)
  : BT::StatefulActionNode(name, config), ContextNode(config) {}
  static BT::PortsList providedPorts() { return {}; }
  BT::NodeStatus onStart() override
  {
    context_->readiness->begin(context_->wait_for_nav2_timeout);
    return onRunning();
  }
  BT::NodeStatus onRunning() override
  {
    const auto status = context_->readiness->poll();
    if (status == Nav2ReadinessCheck::Status::DENIED) {
      return readiness_failure(context_->readiness->reason());
    }
    return status == Nav2ReadinessCheck::Status::ALLOWED ?
      BT::NodeStatus::SUCCESS : BT::NodeStatus::RUNNING;
  }
  void onHalted() override {context_->readiness->reset();}
};

class NavigateNav2 : public BT::StatefulActionNode, private ContextNode
{
public:
  NavigateNav2(const std::string & name, const BT::NodeConfiguration & config)
  : BT::StatefulActionNode(name, config), ContextNode(config) {}

  static BT::PortsList providedPorts()
  {
    return {BT::InputPort<geometry_msgs::msg::PoseStamped>("goal")};
  }

  BT::NodeStatus onStart() override
  {
    context_->readiness->begin(context_->wait_for_nav2_timeout);
    checking_ = true;
    return onRunning();
  }

  BT::NodeStatus send_goal()
  {
    const auto goal = getInput<geometry_msgs::msg::PoseStamped>("goal");
    if (!goal) {
      set_nav_result("REJECTED");
      set_failure("navigate_nav2", "final_goal is absent from blackboard");
      return BT::NodeStatus::FAILURE;
    }
    if (!context_->navigate_client->action_server_is_ready()) {
      set_nav_result("TIMEOUT");
      set_failure("navigate_nav2", "/navigate_to_pose is not ready");
      return BT::NodeStatus::FAILURE;
    }

    started_at_ = std::chrono::steady_clock::now();
    result_ready_ = false;
    result_label_.clear();
    goal_handle_.reset();

    NavigateToPose::Goal nav_goal;
    nav_goal.pose = goal.value();
    rclcpp_action::Client<NavigateToPose>::SendGoalOptions options;
    options.goal_response_callback = [this](GoalHandleNavigateToPose::SharedPtr handle) {
      if (!handle) {
        result_label_ = "REJECTED";
        result_ready_ = true;
        return;
      }
      goal_handle_ = handle;
    };
    options.result_callback = [this](const GoalHandleNavigateToPose::WrappedResult & result) {
      switch (result.code) {
        case rclcpp_action::ResultCode::SUCCEEDED:
          result_label_ = "SUCCEEDED";
          break;
        case rclcpp_action::ResultCode::ABORTED:
          result_label_ = "ABORTED";
          break;
        case rclcpp_action::ResultCode::CANCELED:
          result_label_ = "CANCELED";
          break;
        default:
          result_label_ = "ABORTED";
          break;
      }
      result_ready_ = true;
    };
    context_->metrics->start();
    context_->navigate_client->async_send_goal(nav_goal, options);
    RCLCPP_INFO(context_->node->get_logger(), "Assistive BT N0: final_goal sent to /navigate_to_pose.");
    return BT::NodeStatus::RUNNING;
  }

  BT::NodeStatus onRunning() override
  {
    if (checking_) {
      const auto status = context_->readiness->poll();
      if (status == Nav2ReadinessCheck::Status::CHECKING) return BT::NodeStatus::RUNNING;
      checking_ = false;
      if (status == Nav2ReadinessCheck::Status::DENIED) {
        return readiness_failure(context_->readiness->reason());
      }
      return send_goal();
    }

    if (result_ready_) {
      set_nav_result(result_label_);
      if (result_label_ != "SUCCEEDED") {
        set_failure("navigate_nav2", result_label_);
        return BT::NodeStatus::FAILURE;
      }
      return BT::NodeStatus::SUCCESS;
    }
    if (std::chrono::steady_clock::now() - started_at_ > context_->navigation_timeout) {
      if (goal_handle_) {
        context_->navigate_client->async_cancel_goal(goal_handle_);
      }
      set_nav_result("TIMEOUT");
      set_failure("navigate_nav2", "TIMEOUT waiting for /navigate_to_pose result");
      return BT::NodeStatus::FAILURE;
    }
    return BT::NodeStatus::RUNNING;
  }

  void onHalted() override
  {
    context_->readiness->reset();
    if (goal_handle_) {
      context_->navigate_client->async_cancel_goal(goal_handle_);
    }
  }

private:
  bool checking_{false};
  std::chrono::steady_clock::time_point started_at_;
  GoalHandleNavigateToPose::SharedPtr goal_handle_;
  bool result_ready_{false};
  std::string result_label_;
};

class FinalizeExperiment : public BT::SyncActionNode, private ContextNode
{
public:
  FinalizeExperiment(const std::string & name, const BT::NodeConfiguration & config)
  : BT::SyncActionNode(name, config), ContextNode(config) {}

  static BT::PortsList providedPorts() { return {}; }

  BT::NodeStatus tick() override
  {
    bool finalized = false;
    (void)config_.blackboard->get("experiment_finalized", finalized);
    if (finalized) return BT::NodeStatus::SUCCESS;
    config_.blackboard->set("experiment_finalized", true);
    config_.blackboard->set("finalization_count", 1);

    std::string result;
    if (!config_.blackboard->get("final_goal_nav2_result", result)) {
      set_failure("finalize_experiment", "missing final_goal_nav2_result");
      return BT::NodeStatus::FAILURE;
    }
    const bool succeeded = result == "SUCCEEDED";
    config_.blackboard->set("nav2_result", result);
    config_.blackboard->set("success", succeeded);
    if (!succeeded) {
      std::string existing;
      (void)config_.blackboard->get("failure_stage", existing);
      if (existing.empty()) set_failure("finalize_experiment", result.empty() ? "missing Nav2 result" : result);
      return BT::NodeStatus::FAILURE;
    }
    return BT::NodeStatus::SUCCESS;
  }
};

inline void finalize_n0_experiment(const BT::Blackboard::Ptr & blackboard)
{
  BT::NodeConfiguration config;
  config.blackboard = blackboard;
  FinalizeExperiment finalize("terminal_finalize", config);
  finalize.executeTick();
}

// Called only after the run reaches a terminal state, including BT failures.
inline ResultRow n0_result_row(
  const BT::Blackboard::Ptr & blackboard, const NavigationMetrics & metrics)
{
  ResultRow row;
  for (const auto & field : common_result_fields()) row[field] = "N/A";
  row["timestamp_utc"] = utc_now();
  row["condition"] = "MEMORY_OFF";
  for (const auto * key : {
      "experiment_id", "scenario_id", "run_id", "user_id", "location", "task",
      "goal_label", "final_goal_nav2_result", "nav2_result", "failure_stage", "failure_reason"})
  {
    row[key] = blackboard->get<std::string>(key);
  }
  const auto goal = blackboard->get<geometry_msgs::msg::PoseStamped>("final_goal");
  row["goal_x"] = metric_number(goal.pose.position.x);
  row["goal_y"] = metric_number(goal.pose.position.y);
  row["goal_yaw"] = metric_number(blackboard->get<double>("goal_yaw"));
  row["success"] = blackboard->get<bool>("success") ? "true" : "false";
  row["navigation_time_s"] = metrics.time_s();
  row["distance_m"] = metrics.distance_m();
  row["replanning_count"] = metrics.replanning_count();
  row["initial_x"] = metrics.initial_x();
  row["initial_y"] = metrics.initial_y();
  row["initial_yaw"] = metrics.initial_yaw();
  return row;
}

class AssistiveBtOrchestrator : public rclcpp::Node
{
public:
  AssistiveBtOrchestrator() : Node("assistive_bt_orchestrator")
  {
    declare_parameter<std::string>("experiment_id", "");
    declare_parameter<std::string>("scenario_id", "");
    declare_parameter<std::string>("condition", "MEMORY_OFF");
    declare_parameter<std::string>("run_id", "");
    declare_parameter<std::string>("result_csv", "");
    for (const auto * key : {"user_id", "location", "task", "goal_label"}) {
      declare_parameter<std::string>(key, "N/A");
    }
    declare_parameter<double>("goal_x", 2.5);
    declare_parameter<double>("goal_y", -3.0);
    declare_parameter<double>("goal_yaw", 0.0);
    declare_parameter<double>("wait_for_nav2_timeout_s", 60.0);
    declare_parameter<double>("navigation_timeout_s", 120.0);
    declare_parameter<std::string>("bt_xml_path", "");

    if (get_parameter("condition").as_string() != "MEMORY_OFF") {
      throw std::runtime_error("BT phase 1 accepts only condition=MEMORY_OFF");
    }

    context_ = std::make_shared<ExecutionContext>();
    context_->node = this;
    context_->metrics = std::make_shared<NavigationMetrics>(this);
    context_->wait_for_nav2_timeout = std::chrono::milliseconds(
      static_cast<int>(1000.0 * get_parameter("wait_for_nav2_timeout_s").as_double()));
    context_->navigation_timeout = std::chrono::milliseconds(
      static_cast<int>(1000.0 * get_parameter("navigation_timeout_s").as_double()));
    context_->readiness = std::make_shared<Nav2ReadinessCheck>(this);
    context_->navigate_client = rclcpp_action::create_client<NavigateToPose>(this, "/navigate_to_pose");

    blackboard_ = BT::Blackboard::create();
    blackboard_->set("execution_context", context_);
    blackboard_->set("experiment_id", get_parameter("experiment_id").as_string());
    blackboard_->set("scenario_id", get_parameter("scenario_id").as_string());
    blackboard_->set("condition", std::string("MEMORY_OFF"));
    blackboard_->set("run_id", get_parameter("run_id").as_string());
    for (const auto * key : {"user_id", "location", "task", "goal_label"}) {
      blackboard_->set(key, get_parameter(key).as_string());
    }
    blackboard_->set("goal_yaw", get_parameter("goal_yaw").as_double());

    geometry_msgs::msg::PoseStamped final_goal;
    final_goal.header.frame_id = "map";
    final_goal.pose.position.x = get_parameter("goal_x").as_double();
    final_goal.pose.position.y = get_parameter("goal_y").as_double();
    const double yaw = get_parameter("goal_yaw").as_double();
    final_goal.pose.orientation.z = std::sin(yaw / 2.0);
    final_goal.pose.orientation.w = std::cos(yaw / 2.0);
    blackboard_->set("final_goal", final_goal);
    blackboard_->set("final_goal_nav2_result", std::string("NOT_SENT"));
    blackboard_->set("nav2_result", std::string("NOT_STARTED"));
    blackboard_->set("success", false);
    blackboard_->set("failure_stage", std::string(""));
    blackboard_->set("failure_reason", std::string(""));

    factory_.registerNodeType<WaitForNav2Active>("WaitForNav2Active");
    factory_.registerNodeType<NavigateNav2>("NavigateNav2");
    factory_.registerNodeType<FinalizeExperiment>("FinalizeExperiment");

    std::string xml_path = get_parameter("bt_xml_path").as_string();
    if (xml_path.empty()) {
      xml_path = ament_index_cpp::get_package_share_directory("wheelchair_assistive_bt") +
        "/behavior_trees/n0_assistive_navigation.xml";
    }
    tree_ = factory_.createTreeFromFile(xml_path, blackboard_);
    RCLCPP_INFO(get_logger(), "Assistive BT N0 XML loaded: %s", xml_path.c_str());
    tick_timer_ = create_wall_timer(20ms, std::bind(&AssistiveBtOrchestrator::tick, this));
  }

private:
  void tick()
  {
    if (complete_) {
      return;
    }
    BT::NodeStatus status;
    try {
      status = tree_.tickOnce();
    } catch (const std::exception & error) {
      blackboard_->set("success", false);
      blackboard_->set("failure_stage", std::string("bt_execution"));
      blackboard_->set("failure_reason", std::string(error.what()));
      status = BT::NodeStatus::FAILURE;
    }
    if (status == BT::NodeStatus::RUNNING) {
      return;
    }
    if (status == BT::NodeStatus::FAILURE) {
      finalize_n0_experiment(blackboard_);
    }
    complete_ = true;
    tick_timer_->cancel();
    context_->metrics->stop();
    std::string csv_error;
    const auto csv_path = get_parameter("result_csv").as_string();
    if (!result_writer_.write_once(csv_path, n0_result_row(blackboard_, *context_->metrics), csv_error)) {
      RCLCPP_ERROR(get_logger(), "N0 logging failed: result_csv='%s': %s",
        csv_path.c_str(), csv_error.c_str());
      throw std::runtime_error("N0 experiment result logging failed: " + csv_error);
    }

    std::string experiment_id, scenario_id, condition, run_id, nav2_result, final_result;
    std::string failure_stage, failure_reason;
    bool success = false;
    const auto get_value = [this](const std::string & key, auto & value) {
      if (!blackboard_->get(key, value)) {
        throw std::runtime_error("missing blackboard key: " + key);
      }
    };
    get_value("experiment_id", experiment_id);
    get_value("scenario_id", scenario_id);
    get_value("condition", condition);
    get_value("run_id", run_id);
    get_value("nav2_result", nav2_result);
    get_value("final_goal_nav2_result", final_result);
    get_value("success", success);
    get_value("failure_stage", failure_stage);
    get_value("failure_reason", failure_reason);
    RCLCPP_INFO(
      get_logger(),
      "Assistive BT N0 blackboard: experiment_id=%s scenario_id=%s condition=%s run_id=%s "
      "nav2_result=%s final_goal_nav2_result=%s success=%s failure_stage=%s failure_reason=%s",
      experiment_id.c_str(), scenario_id.c_str(), condition.c_str(), run_id.c_str(),
      nav2_result.c_str(), final_result.c_str(), success ? "true" : "false",
      failure_stage.c_str(), failure_reason.c_str());
    rclcpp::shutdown();
  }

  std::shared_ptr<ExecutionContext> context_;
  BT::BehaviorTreeFactory factory_;
  BT::Tree tree_;
  BT::Blackboard::Ptr blackboard_;
  rclcpp::TimerBase::SharedPtr tick_timer_;
  bool complete_{false};
  CommonResultWriter result_writer_;
};
}  // namespace wheelchair_assistive_bt

#ifndef WHEELCHAIR_ASSISTIVE_BT_N0_LOGGING_TEST
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try {
    rclcpp::spin(std::make_shared<wheelchair_assistive_bt::AssistiveBtOrchestrator>());
  } catch (const std::exception & error) {
    RCLCPP_FATAL(rclcpp::get_logger("assistive_bt_orchestrator"), "%s", error.what());
    if (rclcpp::ok()) rclcpp::shutdown();
    return 1;
  }
  if (rclcpp::ok()) rclcpp::shutdown();
  return 0;
}

#endif  // WHEELCHAIR_ASSISTIVE_BT_N0_LOGGING_TEST
