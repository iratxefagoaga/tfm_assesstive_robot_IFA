#include <gtest/gtest.h>
#include <filesystem>
#include <iterator>
#include <cstdlib>

#define WHEELCHAIR_ASSISTIVE_BT_N0_LOGGING_TEST
#include "../src/assistive_bt_orchestrator.cpp"

namespace wheelchair_assistive_bt
{
namespace
{
const std::string expected_header =
  "timestamp_utc,experiment_id,scenario_id,condition,run_id,user_id,location,task,goal_label,"
  "initial_x,initial_y,initial_yaw,goal_x,goal_y,goal_yaw,success,navigation_time_s,distance_m,"
  "replanning_count,min_clearance_m,memory_ids,source_memory,retrieved_strategy,"
  "strategy_waypoint_enabled,strategy_waypoint_offsets,strategy_applied,selected_waypoint_x,"
  "selected_waypoint_y,waypoint_nav2_result,final_goal_nav2_result,nav2_result,failure_stage,"
  "failure_reason,context_compliance,intervention_appropriate\n";

BT::Blackboard::Ptr result_blackboard(bool success)
{
  auto bb = BT::Blackboard::create();
  for (const auto * key : {
      "experiment_id", "scenario_id", "run_id", "user_id", "location", "task", "goal_label"})
  {
    bb->set(key, std::string(key) + "_value");
  }
  bb->set("success", success);
  bb->set("final_goal_nav2_result", std::string(success ? "SUCCEEDED" : "ABORTED"));
  bb->set("nav2_result", std::string(success ? "SUCCEEDED" : "ABORTED"));
  bb->set("failure_stage", std::string(success ? "" : "navigate_nav2"));
  bb->set("failure_reason", std::string(success ? "" : "aborted, \"obstacle\"\nstop"));
  geometry_msgs::msg::PoseStamped goal;
  goal.pose.position.x = 2.5;
  goal.pose.position.y = -3.0;
  bb->set("final_goal", goal);
  bb->set("goal_yaw", 1.2);
  return bb;
}

nav_msgs::msg::Odometry odometry(double x, double y)
{
  nav_msgs::msg::Odometry msg;
  msg.pose.pose.position.x = x;
  msg.pose.pose.position.y = y;
  msg.pose.pose.orientation.z = std::sin(0.6);
  msg.pose.pose.orientation.w = std::cos(0.6);
  return msg;
}

// Independent CSV reader: quoted commas, escaped quotes and embedded newlines.
std::vector<std::vector<std::string>> read_csv(const std::string & text)
{
  std::vector<std::vector<std::string>> rows;
  std::vector<std::string> row;
  std::string field;
  bool quoted = false;
  for (size_t i = 0; i < text.size(); ++i) {
    const char c = text[i];
    if (c == '"') {
      if (quoted && i + 1 < text.size() && text[i + 1] == '"') {
        field += '"';
        ++i;
      } else {
        quoted = !quoted;
      }
    } else if (!quoted && (c == ',' || c == '\n')) {
      row.push_back(field);
      field.clear();
      if (c == '\n') {
        rows.push_back(row);
        row.clear();
      }
    } else {
      field += c;
    }
  }
  if (quoted || !row.empty() || !field.empty()) throw std::runtime_error("incomplete CSV");
  return rows;
}

class LoggingFile : public ::testing::Test
{
protected:
  void SetUp() override
  {
    char pattern[] = "/tmp/n0_logging_unit_XXXXXX";
    const auto result = mkdtemp(pattern);
    ASSERT_NE(result, nullptr);
    directory = result;
    path = directory + "/result.csv";
  }
  void TearDown() override { std::filesystem::remove_all(directory); }
  std::string contents() const
  {
    std::ifstream file(path);
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
  }
  std::string directory, path;
};

TEST(N0Logging, ExactSchemaAndMemoryOffFields)
{
  NavigationMetrics metrics;
  const auto row = n0_result_row(result_blackboard(true), metrics);
  EXPECT_EQ(common_result_header(), expected_header);
  ASSERT_EQ(row.size(), 35u);
  EXPECT_EQ(row.at("condition"), "MEMORY_OFF");
  for (const auto * key : {
      "memory_ids", "source_memory", "retrieved_strategy", "strategy_waypoint_enabled",
      "strategy_waypoint_offsets", "strategy_applied", "selected_waypoint_x",
      "selected_waypoint_y", "waypoint_nav2_result", "min_clearance_m",
      "context_compliance", "intervention_appropriate"})
  {
    EXPECT_EQ(row.at(key), "N/A") << key;
  }
  EXPECT_EQ(row.at("goal_x"), "2.500");
  EXPECT_EQ(row.at("goal_y"), "-3.000");
  EXPECT_EQ(row.at("goal_yaw"), "1.200");
  EXPECT_EQ(row.at("user_id"), "user_id_value");
  EXPECT_EQ(row.at("navigation_time_s"), "N/A");
  EXPECT_EQ(row.at("distance_m"), "N/A");
  EXPECT_EQ(row.at("replanning_count"), "N/A");
  EXPECT_EQ(row.at("initial_x"), "N/A");
}

TEST(NavigationMetrics, DistanceOnlyBetweenActiveSamples)
{
  NavigationMetrics metrics;
  metrics.observe_odometry(odometry(100, 100));
  metrics.start();
  metrics.observe_odometry(odometry(0, 0));
  EXPECT_EQ(metrics.distance_m(), "0.000");
  metrics.observe_odometry(odometry(3, 4));
  metrics.observe_odometry(odometry(6, 8));
  metrics.stop();
  metrics.observe_odometry(odometry(1000, 1000));
  EXPECT_EQ(metrics.distance_m(), "10.000");
  EXPECT_EQ(metrics.initial_x(), "100.000");
  EXPECT_EQ(metrics.initial_y(), "100.000");
  EXPECT_EQ(metrics.initial_yaw(), "1.200");
}

TEST(NavigationMetrics, ReplanningExcludesFirstPlanAndInactivePlans)
{
  NavigationMetrics metrics;
  metrics.observe_plan();
  metrics.start();
  EXPECT_EQ(metrics.replanning_count(), "0");
  metrics.observe_plan();
  EXPECT_EQ(metrics.replanning_count(), "0");
  metrics.observe_plan();
  metrics.observe_plan();
  EXPECT_EQ(metrics.replanning_count(), "2");
  metrics.stop();
  metrics.observe_plan();
  EXPECT_EQ(metrics.replanning_count(), "2");
}

TEST(NavigationMetrics, DurationFreezesAtRunCompletion)
{
  NavigationMetrics metrics;
  const auto start = NavigationMetrics::Clock::time_point{};
  metrics.start(start);
  metrics.start(start + std::chrono::seconds(1));
  metrics.stop(start + std::chrono::milliseconds(2500));
  EXPECT_EQ(metrics.time_s(), "2.500");
  metrics.stop(start + std::chrono::seconds(100));
  EXPECT_EQ(metrics.time_s(), "2.500");
}

TEST_F(LoggingFile, SuccessAndFailureEachWriteExactlyOneCompleteRow)
{
  NavigationMetrics metrics;
  for (bool success : {true, false}) {
    CommonResultWriter writer;
    std::string error;
    const auto row = n0_result_row(result_blackboard(success), metrics);
    ASSERT_TRUE(writer.write_once(path, row, error)) << error;
    const auto first_write = contents();
    ASSERT_TRUE(writer.write_once(path, row, error)) << error;
    EXPECT_EQ(contents(), first_write);
  }
  const auto csv = read_csv(contents());
  ASSERT_EQ(csv.size(), 3u);  // One header, one success, one failure.
  for (const auto & row : csv) EXPECT_EQ(row.size(), 35u);
  EXPECT_EQ(csv[1][15], "true");
  EXPECT_EQ(csv[2][15], "false");
  EXPECT_EQ(csv[2][29], "ABORTED");
  EXPECT_EQ(csv[2][31], "navigate_nav2");
  EXPECT_EQ(csv[2][32], "aborted, \"obstacle\"\nstop");
}

TEST_F(LoggingFile, FailureBeforeNavigationStillHasOneRow)
{
  NavigationMetrics metrics;
  auto bb = result_blackboard(false);
  bb->set("final_goal_nav2_result", std::string("NOT_SENT"));
  bb->set("nav2_result", std::string("NOT_STARTED"));
  bb->set("failure_stage", std::string("wait_for_nav2_active"));
  CommonResultWriter writer;
  std::string error;
  ASSERT_TRUE(writer.write_once(path, n0_result_row(bb, metrics), error)) << error;
  const auto csv = read_csv(contents());
  ASSERT_EQ(csv.size(), 2u);
  EXPECT_EQ(csv[1][16], "N/A");
  EXPECT_EQ(csv[1][29], "NOT_SENT");
  EXPECT_EQ(csv[1][31], "wait_for_nav2_active");
}

TEST_F(LoggingFile, EmptyExistingFileGetsHeaderAndCsvRoundTrips)
{
  std::ofstream(path).close();
  ResultRow row;
  row["failure_reason"] = "comma, quote\" CR\r LF\n";
  std::string error;
  ASSERT_TRUE(append_common_result(path, row, error)) << error;
  const auto csv = read_csv(contents());
  ASSERT_EQ(csv.size(), 2u);
  EXPECT_EQ(csv[0], common_result_fields());
  EXPECT_EQ(csv[1].size(), 35u);
  EXPECT_EQ(csv[1][32], row.at("failure_reason"));
  EXPECT_EQ(csv_escape("plain"), "plain");
  EXPECT_EQ(csv_escape("a,\"b\""), "\"a,\"\"b\"\"\"");
}

TEST_F(LoggingFile, WriteErrorsAreExplicitAndNotRetried)
{
  ResultRow row;
  std::string error;
  EXPECT_FALSE(append_common_result("", row, error));
  EXPECT_NE(error.find("empty"), std::string::npos);
  CommonResultWriter writer;
  EXPECT_FALSE(writer.write_once(directory + "/missing/result.csv", row, error));
  EXPECT_NE(error.find("cannot open"), std::string::npos);
  EXPECT_FALSE(writer.write_once(path, row, error));
  EXPECT_FALSE(std::filesystem::exists(path));
  std::ofstream(path) << "wrong,header\n";
  EXPECT_FALSE(append_common_result(path, row, error));
  EXPECT_NE(error.find("schema/header mismatch"), std::string::npos);
  EXPECT_EQ(contents(), "wrong,header\n");
}
}  // namespace
}  // namespace wheelchair_assistive_bt
