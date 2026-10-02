#include <chrono>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#include <sstream>
#include <map>
#include <vector>

#include "ament_index_cpp/get_package_share_directory.hpp"
#include "behaviortree_cpp/action_node.h"
#include "behaviortree_cpp/bt_factory.h"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "wheelchair_interfaces/srv/memory_query.hpp"
#include "wheelchair_interfaces/srv/navigation_recommendation.hpp"
#include "wheelchair_assistive_bt/common_experiment_logging.hpp"
#include "wheelchair_assistive_bt/nav2_readiness.hpp"

namespace wheelchair_assistive_bt
{
using namespace std::chrono_literals;
using GetState = lifecycle_msgs::srv::GetState;
using NavigateToPose = nav2_msgs::action::NavigateToPose;
using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;
using MemoryQuery = wheelchair_interfaces::srv::MemoryQuery;
using Recommendation = wheelchair_interfaces::srv::NavigationRecommendation;

struct Context
{
  rclcpp::Node * node{};
  std::shared_ptr<Nav2ReadinessCheck> readiness;
  rclcpp_action::Client<NavigateToPose>::SharedPtr navigate;
  rclcpp::Client<MemoryQuery>::SharedPtr memory_query;
  rclcpp::Client<Recommendation>::SharedPtr recommendation;
  std::chrono::milliseconds memory_timeout{30000};
  std::chrono::milliseconds nav_ready_timeout{60000};
  std::chrono::milliseconds navigation_timeout{120000};
  std::shared_ptr<NavigationMetrics> metrics;
};

class NodeContext
{
protected:
  explicit NodeContext(const BT::NodeConfiguration & config) : config_(config)
  {
    if (!config_.blackboard->get("context", context_)) {
      throw BT::RuntimeError("missing context in blackboard");
    }
  }

  template<typename T>
  T value(const std::string & key) const
  {
    T result{};
    if (!config_.blackboard->get(key, result)) {
      throw BT::RuntimeError("missing blackboard key: " + key);
    }
    return result;
  }

  void failure(const std::string & stage, const std::string & reason)
  {
    config_.blackboard->set("failure_stage", stage);
    config_.blackboard->set("failure_reason", reason);
    config_.blackboard->set("success", false);
  }

  BT::NodeStatus readiness_failure(const std::string & reason)
  {
    config_.blackboard->set("final_goal_nav2_result", std::string("NOT_SENT"));
    config_.blackboard->set("nav2_result", std::string("NOT_SENT"));
    if (value<bool>("strategy_applied") &&
        value<std::string>("waypoint_nav2_result") != "SUCCEEDED") {
      config_.blackboard->set("waypoint_nav2_result", std::string("NOT_SENT"));
    }
    failure("readiness", reason);
    return BT::NodeStatus::FAILURE;
  }

  BT::NodeConfiguration config_;
  std::shared_ptr<Context> context_;
};

class QueryMemory : public BT::StatefulActionNode, private NodeContext
{
public:
  QueryMemory(const std::string & name, const BT::NodeConfiguration & config)
  : BT::StatefulActionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts() { return {}; }

  BT::NodeStatus onStart() override
  {
    started_ = std::chrono::steady_clock::now();
    sent_ = false; done_ = false; response_.reset(); error_.clear();
    config_.blackboard->set("memory_query_result", std::string("PENDING"));
    return BT::NodeStatus::RUNNING;
  }

  BT::NodeStatus onRunning() override
  {
    if (std::chrono::steady_clock::now() - started_ > context_->memory_timeout) {
      return fail("TIMEOUT", "TIMEOUT waiting for /memory/query");
    }
    if (!sent_) {
      if (!context_->memory_query->service_is_ready()) return BT::NodeStatus::RUNNING;
      auto request = std::make_shared<MemoryQuery::Request>();
      request->query = value<std::string>("query");
      request->user_id = value<std::string>("user_id");
      request->location = value<std::string>("location");
      request->task = value<std::string>("task");
      request->goal = value<std::string>("goal_label");
      request->k = value<int32_t>("k");
      sent_ = true;
      RCLCPP_INFO(context_->node->get_logger(), "Assistive BT N1: QueryMemory -> /memory/query");
      context_->memory_query->async_send_request(request, [this](rclcpp::Client<MemoryQuery>::SharedFuture future) {
        try { response_ = future.get(); } catch (const std::exception & error) { error_ = error.what(); }
        done_ = true;
      });
    }
    if (!done_) return BT::NodeStatus::RUNNING;
    if (!error_.empty()) return fail("ERROR", "MemoryQuery error: " + error_);
    if (!response_ || !response_->success) {
      return fail("FAILED", response_ ? "MemoryQuery failed: " + response_->message : "MemoryQuery returned no response");
    }
    if (response_->memory_ids.empty()) return fail("EMPTY_RESPONSE", "MemoryQuery returned no memory_ids");
    config_.blackboard->set("memory_ids", response_->memory_ids);
    config_.blackboard->set("summaries", response_->summaries);
    config_.blackboard->set("observations", response_->observations);
    config_.blackboard->set("actions", response_->actions);
    config_.blackboard->set("outcomes", response_->outcomes);
    config_.blackboard->set("preferences", response_->preferences);
    config_.blackboard->set("semantic_scores", response_->semantic_scores);
    config_.blackboard->set("context_scores", response_->context_scores);
    config_.blackboard->set("final_scores", response_->final_scores);
    config_.blackboard->set("memory_query_result", std::string("SUCCEEDED"));
    return BT::NodeStatus::SUCCESS;
  }
  void onHalted() override {}

private:
  BT::NodeStatus fail(const std::string & result, const std::string & reason)
  {
    config_.blackboard->set("memory_query_result", result);
    failure("query_memory", reason);
    return BT::NodeStatus::FAILURE;
  }
  std::chrono::steady_clock::time_point started_;
  bool sent_{false}, done_{false};
  MemoryQuery::Response::SharedPtr response_;
  std::string error_;
};

class GetNavigationRecommendation : public BT::StatefulActionNode, private NodeContext
{
public:
  GetNavigationRecommendation(const std::string & name, const BT::NodeConfiguration & config)
  : BT::StatefulActionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts() { return {}; }

  BT::NodeStatus onStart() override
  {
    started_ = std::chrono::steady_clock::now();
    sent_ = false; done_ = false; response_.reset(); error_.clear();
    config_.blackboard->set("recommendation_result", std::string("PENDING"));
    return BT::NodeStatus::RUNNING;
  }

  BT::NodeStatus onRunning() override
  {
    if (std::chrono::steady_clock::now() - started_ > context_->memory_timeout) {
      return fail("TIMEOUT", "TIMEOUT waiting for /memory/navigation_recommendation");
    }
    if (!sent_) {
      if (!context_->recommendation->service_is_ready()) return BT::NodeStatus::RUNNING;
      auto request = std::make_shared<Recommendation::Request>();
      request->query = value<std::string>("query");
      request->user_id = value<std::string>("user_id");
      request->location = value<std::string>("location");
      request->task = value<std::string>("task");
      request->goal = value<std::string>("goal_label");
      request->k = value<int32_t>("k");
      sent_ = true;
      RCLCPP_INFO(context_->node->get_logger(), "Assistive BT N1: GetNavigationRecommendation -> /memory/navigation_recommendation");
      context_->recommendation->async_send_request(request, [this](rclcpp::Client<Recommendation>::SharedFuture future) {
        try { response_ = future.get(); } catch (const std::exception & error) { error_ = error.what(); }
        done_ = true;
      });
    }
    if (!done_) return BT::NodeStatus::RUNNING;
    if (!error_.empty()) return fail("ERROR", "NavigationRecommendation error: " + error_);
    if (!response_ || !response_->success) {
      return fail("FAILED", response_ ? "NavigationRecommendation failed: " + response_->message : "NavigationRecommendation returned no response");
    }
    if (response_->strategy.empty() || response_->source_memory.empty()) {
      return fail("INVALID_RESPONSE", "NavigationRecommendation lacks strategy or source_memory");
    }
    config_.blackboard->set("source_memory", response_->source_memory);
    config_.blackboard->set("recommendation_reason", response_->reason);
    config_.blackboard->set("retrieved_strategy", response_->strategy);
    config_.blackboard->set("avoid_obstacle", response_->avoid_obstacle);
    config_.blackboard->set("prefer_clearance", response_->prefer_clearance);
    config_.blackboard->set("recommendation_semantic_score", response_->semantic_score);
    config_.blackboard->set("recommendation_context_score", response_->context_score);
    config_.blackboard->set("recommendation_final_score", response_->final_score);
    config_.blackboard->set("recommendation_result", std::string("SUCCEEDED"));
    return BT::NodeStatus::SUCCESS;
  }
  void onHalted() override {}

private:
  BT::NodeStatus fail(const std::string & result, const std::string & reason)
  {
    config_.blackboard->set("recommendation_result", result);
    failure("get_navigation_recommendation", reason);
    return BT::NodeStatus::FAILURE;
  }
  std::chrono::steady_clock::time_point started_;
  bool sent_{false}, done_{false};
  Recommendation::Response::SharedPtr response_;
  std::string error_;
};

class WaitForNav2Active : public BT::StatefulActionNode, private NodeContext
{
public:
  WaitForNav2Active(const std::string & name, const BT::NodeConfiguration & config)
  : BT::StatefulActionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts() { return {}; }
  BT::NodeStatus onStart() override
  {
    context_->readiness->begin(context_->nav_ready_timeout);
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

class ResolveStrategyWaypoint : public BT::SyncActionNode, private NodeContext
{
public:
 ResolveStrategyWaypoint(const std::string & n,const BT::NodeConfiguration & c):BT::SyncActionNode(n,c),NodeContext(c){}
 static BT::PortsList providedPorts(){return {};}
 BT::NodeStatus tick() override {
  const auto strategy=value<std::string>("retrieved_strategy"); const auto offsets=value<std::string>("strategy_waypoint_offsets"); const bool enabled=value<bool>("strategy_waypoint_enabled"); const auto goal=value<geometry_msgs::msg::PoseStamped>("final_goal");
  config_.blackboard->set("strategy_applied",false); config_.blackboard->set("waypoint_nav2_result",std::string("NOT_APPLIED")); geometry_msgs::msg::PoseStamped empty; config_.blackboard->set("selected_waypoint",empty);
  if(!enabled || strategy=="direct" || strategy.empty() || offsets.empty()) return BT::NodeStatus::SUCCESS;
  auto trim=[](std::string s){const auto a=s.find_first_not_of(" \t");const auto b=s.find_last_not_of(" \t");return a==std::string::npos?std::string():s.substr(a,b-a+1);};
  std::map<std::string,std::pair<double,double>> parsed; std::stringstream list(offsets); std::string entry;
  while(std::getline(list,entry,',')){std::stringstream f(entry);std::string name,x,y,extra;if(!std::getline(f,name,':')||!std::getline(f,x,':')||!std::getline(f,y,':')||std::getline(f,extra,':')) return invalid("malformed offset entry"); name=trim(name);x=trim(x);y=trim(y);if(name.empty()||parsed.count(name)) return invalid(name.empty()?"empty strategy":"duplicate strategy: "+name);try{size_t px=0,py=0;double dx=std::stod(x,&px),dy=std::stod(y,&py);if(px!=x.size()||py!=y.size())return invalid("non-numeric offset");parsed[name]={dx,dy};}catch(...){return invalid("non-numeric offset");}}
  const auto it=parsed.find(strategy);if(it==parsed.end()||(it->second.first==0.0&&it->second.second==0.0))return BT::NodeStatus::SUCCESS;auto waypoint=goal;waypoint.pose.position.x+=it->second.first;waypoint.pose.position.y+=it->second.second;config_.blackboard->set("selected_waypoint",waypoint);config_.blackboard->set("strategy_applied",true);return BT::NodeStatus::SUCCESS;
 }
private:
 BT::NodeStatus invalid(const std::string& reason){failure("resolve_strategy_waypoint",reason);config_.blackboard->set("final_goal_nav2_result",std::string("NOT_SENT"));return BT::NodeStatus::FAILURE;}
};

class WaypointApplicable : public BT::ConditionNode, private NodeContext
{
public:
  WaypointApplicable(const std::string & name, const BT::NodeConfiguration & config)
  : BT::ConditionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts() { return {}; }
  BT::NodeStatus tick() override
  {
    return value<bool>("strategy_applied") ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
  }
};

class WaypointNotApplicable : public BT::ConditionNode, private NodeContext
{
public:
  WaypointNotApplicable(const std::string & name, const BT::NodeConfiguration & config)
  : BT::ConditionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts() { return {}; }
  BT::NodeStatus tick() override
  {
    return value<bool>("strategy_applied") ? BT::NodeStatus::FAILURE : BT::NodeStatus::SUCCESS;
  }
};
class NavigateNav2 : public BT::StatefulActionNode, private NodeContext
{
public:
  NavigateNav2(const std::string & name, const BT::NodeConfiguration & config)
  : BT::StatefulActionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts()
  {
    return {BT::InputPort<geometry_msgs::msg::PoseStamped>("goal"), BT::InputPort<std::string>("stage")};
  }
  BT::NodeStatus onStart() override
  {
    context_->readiness->begin(context_->nav_ready_timeout);
    checking_ = true;
    return onRunning();
  }

  BT::NodeStatus send_goal()
  {
    const auto goal = getInput<geometry_msgs::msg::PoseStamped>("goal");
    const auto stage = getInput<std::string>("stage");
    stage_ = stage ? stage.value() : "final_goal";
    if (stage_ != "waypoint" && stage_ != "final_goal") {
      return fail("REJECTED", "invalid NavigateNav2 stage: " + stage_);
    }
    if (!goal) return fail("REJECTED", stage_ + " is absent from blackboard");
    if (!context_->navigate->action_server_is_ready()) return fail("TIMEOUT", "/navigate_to_pose is not ready");
    started_ = std::chrono::steady_clock::now(); done_ = false; result_.clear(); handle_.reset();
    NavigateToPose::Goal request; request.pose = goal.value();
    rclcpp_action::Client<NavigateToPose>::SendGoalOptions options;
    options.goal_response_callback = [this](GoalHandle::SharedPtr handle) { if (!handle) { result_ = "REJECTED"; done_ = true; } else handle_ = handle; };
    options.result_callback = [this](const GoalHandle::WrappedResult & wrapped) {
      result_ = wrapped.code == rclcpp_action::ResultCode::SUCCEEDED ? "SUCCEEDED" :
        wrapped.code == rclcpp_action::ResultCode::CANCELED ? "CANCELED" : "ABORTED";
      done_ = true;
    };
    if (context_->metrics) context_->metrics->start();
    context_->navigate->async_send_goal(request, options);
    RCLCPP_INFO(context_->node->get_logger(), "Assistive BT N1: %s sent to /navigate_to_pose", stage_.c_str());
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

    if (done_) return result_ == "SUCCEEDED" ? success() : fail(result_, result_);
    if (std::chrono::steady_clock::now() - started_ > context_->navigation_timeout) {
      if (handle_) context_->navigate->async_cancel_goal(handle_);
      return fail("TIMEOUT", "TIMEOUT waiting for /navigate_to_pose result");
    }
    return BT::NodeStatus::RUNNING;
  }
  void onHalted() override { context_->readiness->reset(); if (handle_) context_->navigate->async_cancel_goal(handle_); }
private:
  bool checking_{false};
  BT::NodeStatus success()
  {
    if (stage_ == "waypoint") {
      config_.blackboard->set("waypoint_nav2_result", std::string("SUCCEEDED"));
    } else {
      config_.blackboard->set("final_goal_nav2_result", std::string("SUCCEEDED"));
      config_.blackboard->set("nav2_result", std::string("SUCCEEDED"));
      config_.blackboard->set("success", true);
    }
    return BT::NodeStatus::SUCCESS;
  }
  BT::NodeStatus fail(const std::string & result, const std::string & reason)
  {
    if (stage_ == "waypoint") {
      config_.blackboard->set("waypoint_nav2_result", result);
      config_.blackboard->set("final_goal_nav2_result", std::string("NOT_SENT"));
      config_.blackboard->set("nav2_result", result);
      failure("navigate_waypoint", reason);
    } else {
      config_.blackboard->set("final_goal_nav2_result", result);
      config_.blackboard->set("nav2_result", result);
      failure("navigate_nav2", reason);
    }
    return BT::NodeStatus::FAILURE;
  }
  std::chrono::steady_clock::time_point started_;
  GoalHandle::SharedPtr handle_; bool done_{false}; std::string result_, stage_{"final_goal"};
};

class FinalizeExperiment : public BT::SyncActionNode, private NodeContext
{
public:
  FinalizeExperiment(const std::string & name, const BT::NodeConfiguration & config)
  : BT::SyncActionNode(name, config), NodeContext(config) {}
  static BT::PortsList providedPorts() { return {}; }
  BT::NodeStatus tick() override
  {
    bool finalized = false;
    (void)config_.blackboard->get("experiment_finalized", finalized);
    if (finalized) return BT::NodeStatus::SUCCESS;
    config_.blackboard->set("experiment_finalized", true);
    config_.blackboard->set("finalization_count", 1);

    const auto result = value<std::string>("final_goal_nav2_result");
    if (result == "SUCCEEDED") return BT::NodeStatus::SUCCESS;
    std::string existing;
    (void)config_.blackboard->get("failure_stage", existing);
    if (existing.empty()) failure("finalize_experiment", result.empty() ? "missing Nav2 result" : result);
    return BT::NodeStatus::FAILURE;
  }
};

inline void finalize_n1_experiment(const BT::Blackboard::Ptr & blackboard)
{
  BT::NodeConfiguration config;
  config.blackboard = blackboard;
  FinalizeExperiment finalize("terminal_finalize", config);
  finalize.executeTick();
}

// Snapshot only at terminal run state; unknown memory data remains N/A.
inline ResultRow n1_result_row(
  const BT::Blackboard::Ptr & blackboard, const NavigationMetrics & metrics)
{
  ResultRow row;
  for (const auto & field : common_result_fields()) row[field] = "N/A";
  row["timestamp_utc"] = utc_now();
  row["condition"] = "MEMORY_ON";
  for (const auto * key : {
      "experiment_id", "scenario_id", "run_id", "user_id", "location", "task",
      "goal_label", "waypoint_nav2_result", "final_goal_nav2_result",
      "nav2_result", "failure_stage", "failure_reason"})
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
  const auto ids = blackboard->get<std::vector<std::string>>("memory_ids");
  if (!ids.empty()) {
    std::string joined;
    for (const auto & id : ids) joined += (joined.empty() ? "" : "|") + id;
    row["memory_ids"] = joined;
  }
  row["strategy_waypoint_enabled"] =
    blackboard->get<bool>("strategy_waypoint_enabled") ? "true" : "false";
  const auto offsets = blackboard->get<std::string>("strategy_waypoint_offsets");
  if (!offsets.empty()) row["strategy_waypoint_offsets"] = offsets;
  if (blackboard->get<std::string>("recommendation_result") == "SUCCEEDED") {
    for (const auto * key : {"source_memory", "retrieved_strategy"}) {
      const auto value = blackboard->get<std::string>(key);
      if (!value.empty()) row[key] = value;
    }
    const bool applied = blackboard->get<bool>("strategy_applied");
    row["strategy_applied"] = applied ? "true" : "false";
    if (applied) {
      const auto waypoint = blackboard->get<geometry_msgs::msg::PoseStamped>("selected_waypoint");
      row["selected_waypoint_x"] = metric_number(waypoint.pose.position.x);
      row["selected_waypoint_y"] = metric_number(waypoint.pose.position.y);
    }
  }
  return row;
}

inline bool finalize_n1_logging(
  const BT::Blackboard::Ptr & blackboard, NavigationMetrics & metrics,
  CommonResultWriter & writer, const std::string & path, std::string & error,
  NavigationMetrics::Clock::time_point now = NavigationMetrics::Clock::now())
{
  metrics.stop(now);
  return writer.write_once(path, n1_result_row(blackboard, metrics), error);
}

class MemoryObservationOrchestrator : public rclcpp::Node
{
public:
  MemoryObservationOrchestrator() : Node("memory_observation_bt_orchestrator")
  {
    declare_parameter<std::string>("experiment_id", ""); declare_parameter<std::string>("scenario_id", "");
    declare_parameter<std::string>("run_id", ""); declare_parameter<std::string>("query", "");
    declare_parameter<std::string>("user_id", ""); declare_parameter<std::string>("location", "");
    declare_parameter<std::string>("task", ""); declare_parameter<std::string>("goal_label", "");
    declare_parameter<int>("k", 5); declare_parameter<double>("goal_x", 2.5); declare_parameter<double>("goal_y", -3.0);
    declare_parameter<double>("goal_yaw", 0.0); declare_parameter<double>("memory_timeout_s", 30.0);
    declare_parameter<double>("wait_for_nav2_timeout_s", 60.0); declare_parameter<double>("navigation_timeout_s", 120.0);
    declare_parameter<std::string>("strategy_waypoint_offsets", ""); declare_parameter<bool>("strategy_waypoint_enabled", true); declare_parameter<std::string>("result_csv", "");
    declare_parameter<std::string>("bt_xml_path", "");
    if (get_parameter("query").as_string().empty() || get_parameter("goal_label").as_string().empty()) {
      throw std::runtime_error("MEMORY_ON requires non-empty query and goal_label");
    }
    context_ = std::make_shared<Context>(); context_->node = this;
    context_->memory_timeout = duration("memory_timeout_s"); context_->nav_ready_timeout = duration("wait_for_nav2_timeout_s");
    context_->navigation_timeout = duration("navigation_timeout_s");
    context_->memory_query = create_client<MemoryQuery>("/memory/query");
    context_->recommendation = create_client<Recommendation>("/memory/navigation_recommendation");
    context_->readiness = std::make_shared<Nav2ReadinessCheck>(this);
    context_->navigate = rclcpp_action::create_client<NavigateToPose>(this, "/navigate_to_pose");
    context_->metrics = std::make_shared<NavigationMetrics>(this);
    blackboard_ = BT::Blackboard::create(); blackboard_->set("context", context_);
    blackboard_->set("experiment_id", get_parameter("experiment_id").as_string()); blackboard_->set("scenario_id", get_parameter("scenario_id").as_string());
    blackboard_->set("condition", std::string("MEMORY_ON")); blackboard_->set("run_id", get_parameter("run_id").as_string());
    blackboard_->set("query", get_parameter("query").as_string()); blackboard_->set("user_id", get_parameter("user_id").as_string());
    blackboard_->set("location", get_parameter("location").as_string()); blackboard_->set("task", get_parameter("task").as_string());
    blackboard_->set("goal_label", get_parameter("goal_label").as_string()); blackboard_->set("k", static_cast<int32_t>(get_parameter("k").as_int()));
    blackboard_->set("memory_ids", std::vector<std::string>{}); blackboard_->set("summaries", std::vector<std::string>{});
    blackboard_->set("observations", std::vector<std::string>{}); blackboard_->set("actions", std::vector<std::string>{});
    blackboard_->set("outcomes", std::vector<std::string>{}); blackboard_->set("preferences", std::vector<std::string>{});
    blackboard_->set("semantic_scores", std::vector<double>{}); blackboard_->set("context_scores", std::vector<double>{}); blackboard_->set("final_scores", std::vector<double>{});
    blackboard_->set("source_memory", std::string("")); blackboard_->set("recommendation_reason", std::string(""));
    blackboard_->set("retrieved_strategy", std::string("")); blackboard_->set("avoid_obstacle", false); blackboard_->set("prefer_clearance", false);
    blackboard_->set("recommendation_semantic_score", 0.0); blackboard_->set("recommendation_context_score", 0.0); blackboard_->set("recommendation_final_score", 0.0);
    blackboard_->set("memory_query_result", std::string("NOT_STARTED")); blackboard_->set("recommendation_result", std::string("NOT_STARTED"));
    blackboard_->set("strategy_waypoint_offsets", get_parameter("strategy_waypoint_offsets").as_string());
    blackboard_->set("strategy_waypoint_enabled", get_parameter("strategy_waypoint_enabled").as_bool()); blackboard_->set("result_csv", get_parameter("result_csv").as_string());
    blackboard_->set("strategy_applied", false); blackboard_->set("waypoint_nav2_result", std::string("NOT_APPLIED"));
    geometry_msgs::msg::PoseStamped selected_waypoint; blackboard_->set("selected_waypoint", selected_waypoint); blackboard_->set("final_goal_nav2_result", std::string("NOT_SENT")); blackboard_->set("nav2_result", std::string("NOT_STARTED"));
    blackboard_->set("success", false); blackboard_->set("failure_stage", std::string("")); blackboard_->set("failure_reason", std::string(""));
    geometry_msgs::msg::PoseStamped goal; goal.header.frame_id = "map"; goal.pose.position.x = get_parameter("goal_x").as_double(); goal.pose.position.y = get_parameter("goal_y").as_double();
    blackboard_->set("goal_yaw", get_parameter("goal_yaw").as_double());
    const double yaw = get_parameter("goal_yaw").as_double(); goal.pose.orientation.z = std::sin(yaw / 2.0); goal.pose.orientation.w = std::cos(yaw / 2.0); blackboard_->set("final_goal", goal);
    factory_.registerNodeType<QueryMemory>("QueryMemory"); factory_.registerNodeType<GetNavigationRecommendation>("GetNavigationRecommendation");
    factory_.registerNodeType<ResolveStrategyWaypoint>("ResolveStrategyWaypoint"); factory_.registerNodeType<WaypointApplicable>("WaypointApplicable"); factory_.registerNodeType<WaypointNotApplicable>("WaypointNotApplicable");
    factory_.registerNodeType<WaitForNav2Active>("WaitForNav2Active"); factory_.registerNodeType<NavigateNav2>("NavigateNav2"); factory_.registerNodeType<FinalizeExperiment>("FinalizeExperiment");
    auto xml = get_parameter("bt_xml_path").as_string();
    if (xml.empty()) xml = ament_index_cpp::get_package_share_directory("wheelchair_assistive_bt") + "/behavior_trees/n1_memory_strategy_navigation.xml";
    tree_ = factory_.createTreeFromFile(xml, blackboard_); RCLCPP_INFO(get_logger(), "Assistive BT MEMORY_ON XML loaded: %s", xml.c_str());
    timer_ = create_wall_timer(20ms, std::bind(&MemoryObservationOrchestrator::tick, this));
  }
private:
  std::chrono::milliseconds duration(const std::string & key) const { return std::chrono::milliseconds(static_cast<int>(get_parameter(key).as_double() * 1000.0)); }
  template<typename T> T bb(const std::string & key) const { T result{}; if (!blackboard_->get(key, result)) throw std::runtime_error("missing blackboard key: " + key); return result; }
  static std::string join(const std::vector<std::string> & values) { std::string text; for (const auto & value : values) text += (text.empty() ? "" : "|") + value; return text; }
  static std::string join(const std::vector<double> & values) { std::string text; for (const auto value : values) text += (text.empty() ? "" : "|") + std::to_string(value); return text; }
  void tick()
  {
    if (done_) return;
    BT::NodeStatus status;
    try {
      status = tree_.tickOnce();
    } catch (const std::exception & error) {
      blackboard_->set("success", false);
      blackboard_->set("failure_stage", std::string("bt_execution"));
      blackboard_->set("failure_reason", std::string(error.what()));
      status = BT::NodeStatus::FAILURE;
    }
    if (status == BT::NodeStatus::RUNNING) return;
    if (status == BT::NodeStatus::FAILURE) {
      finalize_n1_experiment(blackboard_);
    }
    done_ = true;
    timer_->cancel();
    std::string csv_error;
    const auto path = get_parameter("result_csv").as_string();
    if (!finalize_n1_logging(blackboard_, *context_->metrics, result_writer_, path, csv_error)) {
      RCLCPP_ERROR(get_logger(), "N1 logging failed: result_csv='%s': %s",
        path.c_str(), csv_error.c_str());
      throw std::runtime_error("N1 experiment result logging failed: " + csv_error);
    }
    const auto goal = bb<geometry_msgs::msg::PoseStamped>("final_goal");
    RCLCPP_INFO(get_logger(), "Assistive BT MEMORY_ON blackboard: experiment_id=%s scenario_id=%s condition=%s run_id=%s query=%s user_id=%s location=%s task=%s goal_label=%s k=%d memory_ids=%s semantic_scores=%s context_scores=%s final_scores=%s source_memory=%s retrieved_strategy=%s recommendation_reason=%s avoid_obstacle=%s prefer_clearance=%s memory_query_result=%s recommendation_result=%s strategy_waypoint_offsets=%s strategy_applied=%s selected_waypoint=(%.3f,%.3f) waypoint_nav2_result=%s final_goal=(%.3f,%.3f) final_goal_nav2_result=%s nav2_result=%s success=%s failure_stage=%s failure_reason=%s", bb<std::string>("experiment_id").c_str(), bb<std::string>("scenario_id").c_str(), bb<std::string>("condition").c_str(), bb<std::string>("run_id").c_str(), bb<std::string>("query").c_str(), bb<std::string>("user_id").c_str(), bb<std::string>("location").c_str(), bb<std::string>("task").c_str(), bb<std::string>("goal_label").c_str(), bb<int32_t>("k"), join(bb<std::vector<std::string>>("memory_ids")).c_str(), join(bb<std::vector<double>>("semantic_scores")).c_str(), join(bb<std::vector<double>>("context_scores")).c_str(), join(bb<std::vector<double>>("final_scores")).c_str(), bb<std::string>("source_memory").c_str(), bb<std::string>("retrieved_strategy").c_str(), bb<std::string>("recommendation_reason").c_str(), bb<bool>("avoid_obstacle") ? "true" : "false", bb<bool>("prefer_clearance") ? "true" : "false", bb<std::string>("memory_query_result").c_str(), bb<std::string>("recommendation_result").c_str(), bb<std::string>("strategy_waypoint_offsets").c_str(), bb<bool>("strategy_applied") ? "true" : "false", bb<geometry_msgs::msg::PoseStamped>("selected_waypoint").pose.position.x, bb<geometry_msgs::msg::PoseStamped>("selected_waypoint").pose.position.y, bb<std::string>("waypoint_nav2_result").c_str(), goal.pose.position.x, goal.pose.position.y, bb<std::string>("final_goal_nav2_result").c_str(), bb<std::string>("nav2_result").c_str(), bb<bool>("success") ? "true" : "false", bb<std::string>("failure_stage").c_str(), bb<std::string>("failure_reason").c_str());
    rclcpp::shutdown();
  }
  CommonResultWriter result_writer_;
  std::shared_ptr<Context> context_; BT::BehaviorTreeFactory factory_; BT::Tree tree_; BT::Blackboard::Ptr blackboard_; rclcpp::TimerBase::SharedPtr timer_; bool done_{false};
};
}  // namespace wheelchair_assistive_bt

// Allow tests to exercise the production node without starting ROS.
#ifndef WHEELCHAIR_ASSISTIVE_BT_RESOLVER_TEST
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try { rclcpp::spin(std::make_shared<wheelchair_assistive_bt::MemoryObservationOrchestrator>()); }
  catch (const std::exception & error) {
    RCLCPP_FATAL(rclcpp::get_logger("memory_observation_bt_orchestrator"), "%s", error.what());
    if (rclcpp::ok()) rclcpp::shutdown();
    return 1;
  }
  if (rclcpp::ok()) rclcpp::shutdown();
  return 0;
}
#endif  // WHEELCHAIR_ASSISTIVE_BT_RESOLVER_TEST
