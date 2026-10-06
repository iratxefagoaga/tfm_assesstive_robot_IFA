#pragma once

#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <locale>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include "nav_msgs/msg/odometry.hpp"
#include "nav_msgs/msg/path.hpp"
#include "rclcpp/rclcpp.hpp"

namespace wheelchair_assistive_bt
{
inline const std::vector<std::string> & common_result_fields() { static const std::vector<std::string> f{"timestamp_utc","experiment_id","scenario_id","condition","run_id","user_id","location","task","goal_label","initial_x","initial_y","initial_yaw","goal_x","goal_y","goal_yaw","success","navigation_time_s","distance_m","replanning_count","min_clearance_m","memory_ids","source_memory","retrieved_strategy","strategy_waypoint_enabled","strategy_waypoint_offsets","strategy_applied","selected_waypoint_x","selected_waypoint_y","waypoint_nav2_result","final_goal_nav2_result","nav2_result","failure_stage","failure_reason","context_compliance","intervention_appropriate","memory_latency_ms"}; return f; }

using ResultRow = std::map<std::string, std::string>;

inline std::string csv_escape(const std::string & value)
{
  if (value.find_first_of(",\"\n\r") == std::string::npos) return value;
  std::string escaped = "\"";
  for (char c : value) escaped += c == '"' ? "\"\"" : std::string(1, c);
  return escaped + "\"";
}

inline std::string utc_now()
{
  const auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
  std::tm utc{};
  gmtime_r(&now, &utc);
  std::ostringstream out;
  out << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
  return out.str();
}

inline std::string metric_number(double value)
{
  std::ostringstream out;
  out.imbue(std::locale::classic());
  out << std::fixed << std::setprecision(3) << value;
  return out.str();
}

// Observational pipeline timing only. Timeout timers and navigation are separate.
class MemoryPipelineLatency
{
public:
  using Clock = std::chrono::steady_clock;
  void reset() { started_.reset(); stopped_.reset(); }
  void start(Clock::time_point now = Clock::now())
  {
    if (!started_) started_ = now;
  }
  void finish(Clock::time_point now = Clock::now())
  {
    if (started_ && !stopped_ && now >= *started_) stopped_ = now;
  }
  std::string milliseconds() const
  {
    return started_ && stopped_ ? metric_number(
      std::chrono::duration<double, std::milli>(*stopped_ - *started_).count()) : "N/A";
  }
private:
  std::optional<Clock::time_point> started_, stopped_;
};

class NavigationMetrics
{
public:
  using Clock = std::chrono::steady_clock;
  // The default constructor supports deterministic unit tests of the same callbacks.
  NavigationMetrics() = default;
  explicit NavigationMetrics(rclcpp::Node * node)
  {
    odom_ = node->create_subscription<nav_msgs::msg::Odometry>(
      "/odom", 20, [this](const nav_msgs::msg::Odometry::SharedPtr msg) {
        observe_odometry(*msg);
      });
    plan_ = node->create_subscription<nav_msgs::msg::Path>(
      "/plan", 10, [this](const nav_msgs::msg::Path::SharedPtr) { observe_plan(); });
  }

  void start(Clock::time_point now = Clock::now())
  {
    if (active_) return;
    active_ = true;
    started_ = now;
    stopped_.reset();
    previous_.reset();
    initial_ = latest_;
    distance_ = 0.0;
    plans_ = 0;
  }

  void stop(Clock::time_point now = Clock::now())
  {
    if (active_) stopped_ = now;
    active_ = false;
  }

  void observe_odometry(const nav_msgs::msg::Odometry & msg)
  {
    latest_ = msg.pose.pose;
    if (!active_) return;
    if (!initial_) initial_ = latest_;
    const auto point = std::make_pair(msg.pose.pose.position.x, msg.pose.pose.position.y);
    if (previous_) {
      distance_ += std::hypot(point.first - previous_->first, point.second - previous_->second);
    }
    previous_ = point;
  }

  void observe_plan() { if (active_) ++plans_; }

  std::string time_s() const
  {
    return started_ ? metric_number(std::chrono::duration<double>(
      stopped_.value_or(Clock::now()) - *started_).count()) : "N/A";
  }
  std::string distance_m() const { return started_ ? metric_number(distance_) : "N/A"; }
  std::string replanning_count() const
  {
    return started_ ? std::to_string(std::max(0, plans_ - 1)) : "N/A";
  }
  std::string initial_x() const
  {
    return initial_ ? metric_number(initial_->position.x) : "N/A";
  }
  std::string initial_y() const
  {
    return initial_ ? metric_number(initial_->position.y) : "N/A";
  }
  std::string initial_yaw() const
  {
    if (!initial_) return "N/A";
    const auto & q = initial_->orientation;
    return metric_number(std::atan2(
      2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z)));
  }

private:
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_;
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr plan_;
  bool active_{false};
  std::optional<Clock::time_point> started_, stopped_;
  std::optional<std::pair<double, double>> previous_;
  std::optional<geometry_msgs::msg::Pose> latest_, initial_;
  double distance_{0.0};
  int plans_{0};
};

inline std::string serialize_common_result(const ResultRow & row)
{
  std::ostringstream out;
  const auto & fields = common_result_fields();
  for (size_t i = 0; i < fields.size(); ++i) {
    if (i) out << ',';
    const auto value = row.find(fields[i]);
    out << csv_escape(value == row.end() ? "N/A" : value->second);
  }
  return out.str() + '\n';
}

inline std::string common_result_header()
{
  ResultRow header;
  for (const auto & field : common_result_fields()) header[field] = field;
  return serialize_common_result(header);
}

inline bool append_common_result(
  const std::string & path, const ResultRow & row, std::string & error)
{
  error.clear();
  if (path.empty()) {
    error = "result_csv parameter is empty";
    return false;
  }
  std::ifstream input(path);
  const bool has_content = input.peek() != std::ifstream::traits_type::eof();
  if (has_content) {
    std::string header;
    std::getline(input, header);
    if (header + '\n' != common_result_header()) {
      error = "result_csv schema/header mismatch: " + path;
      return false;
    }
  }
  input.close();
  // Prepare a complete row before touching the output stream.
  const auto payload = (has_content ? std::string() : common_result_header()) +
    serialize_common_result(row);
  std::ofstream output(path, std::ios::app);
  if (!output) {
    error = "cannot open result_csv: " + path;
    return false;
  }
  output << payload;
  output.flush();
  const bool flushed = output.good();
  output.close();
  if (!flushed || output.fail()) {
    error = "cannot write/flush/close result_csv: " + path;
    return false;
  }
  return true;
}

// One instance per run. A failed write is reported, never retried implicitly.
class CommonResultWriter
{
public:
  bool write_once(const std::string & path, const ResultRow & row, std::string & error)
  {
    if (!attempted_) {
      attempted_ = true;
      written_ = append_common_result(path, row, error_);
    }
    error = error_;
    return written_;
  }

private:
  bool attempted_{false};
  bool written_{false};
  std::string error_;
};
}  // namespace wheelchair_assistive_bt
