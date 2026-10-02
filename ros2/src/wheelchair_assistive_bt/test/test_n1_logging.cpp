#include <gtest/gtest.h>
#include <filesystem>
#include <iterator>
#include <cstdlib>

#define WHEELCHAIR_ASSISTIVE_BT_RESOLVER_TEST
#include "../src/memory_observation_orchestrator.cpp"

wheelchair_assistive_bt::ResultRow n0_reference_row(
  const BT::Blackboard::Ptr &, const wheelchair_assistive_bt::NavigationMetrics &);

namespace wheelchair_assistive_bt
{
namespace
{
BT::Blackboard::Ptr base_result()
{
  auto bb = BT::Blackboard::create();
  bb->set("context", std::make_shared<Context>());
  for (const auto * key : {"experiment_id", "scenario_id", "run_id", "user_id",
      "location", "task", "goal_label"})
  {
    bb->set(key, std::string(key) + "_value");
  }
  bb->set("success", true);
  bb->set("failure_stage", std::string(""));
  bb->set("failure_reason", std::string(""));
  bb->set("nav2_result", std::string("SUCCEEDED"));
  bb->set("final_goal_nav2_result", std::string("SUCCEEDED"));
  bb->set("waypoint_nav2_result", std::string("SUCCEEDED"));
  bb->set("memory_ids", std::vector<std::string>{"M001", "M046"});
  bb->set("source_memory", std::string("M001"));
  bb->set("retrieved_strategy", std::string("west"));
  bb->set("recommendation_result", std::string("SUCCEEDED"));
  bb->set("strategy_waypoint_enabled", true);
  bb->set("strategy_waypoint_offsets", std::string("west:-0.25:0.0"));
  bb->set("strategy_applied", true);
  geometry_msgs::msg::PoseStamped goal;
  goal.header.frame_id = "map";
  goal.pose.position.x = 2.5;
  goal.pose.position.y = -3.0;
  goal.pose.orientation.z = std::sin(0.6);
  goal.pose.orientation.w = std::cos(0.6);
  bb->set("final_goal", goal);
  bb->set("goal_yaw", 1.2);
  goal.pose.position.x = 2.25;
  bb->set("selected_waypoint", goal);
  return bb;
}

nav_msgs::msg::Odometry odom(double x, double y)
{
  nav_msgs::msg::Odometry msg;
  msg.pose.pose.position.x = x;
  msg.pose.pose.position.y = y;
  return msg;
}

class N1Logging : public ::testing::Test
{
protected:
  void SetUp() override
  {
    char pattern[] = "/tmp/n1_logging_unit_XXXXXX";
    const auto result = mkdtemp(pattern);
    ASSERT_NE(result, nullptr);
    directory = result;
    path = directory + "/n1.csv";
  }
  void TearDown() override { std::filesystem::remove_all(directory); }
  std::vector<std::string> lines(const std::string & file)
  {
    std::ifstream in(file);
    std::vector<std::string> result;
    for (std::string line; std::getline(in, line);) result.push_back(line);
    return result;
  }
  std::string directory, path;
};

struct Outcome
{
  const char * name;
  const char * stage;
  const char * nav_result;
  bool applied;
};
class N1Outcomes : public N1Logging, public ::testing::WithParamInterface<Outcome> {};

TEST_P(N1Outcomes, OneFinalRowWithCorrectMemoryAndFailureState)
{
  const auto input = GetParam();
  auto bb = base_result();
  const std::string stage = input.stage;
  const bool early = stage == "query_memory" || stage == "get_navigation_recommendation";
  bb->set("strategy_applied", input.applied);
  bb->set("success", stage.empty());
  bb->set("failure_stage", stage);
  bb->set("failure_reason", stage.empty() ? std::string("") : std::string("failed"));
  bb->set("nav2_result", std::string(input.nav_result));
  bb->set("final_goal_nav2_result",
    std::string(early || stage == "navigate_waypoint" || stage == "resolve_strategy_waypoint" ?
      "NOT_SENT" : input.nav_result));
  bb->set("waypoint_nav2_result", std::string(input.applied ?
    (stage == "navigate_waypoint" ? input.nav_result : "SUCCEEDED") : "NOT_APPLIED"));
  if (early) {
    bb->set("recommendation_result", std::string("FAILED"));
    bb->set("source_memory", std::string(""));
    bb->set("retrieved_strategy", std::string(""));
    if (stage == "query_memory") bb->set("memory_ids", std::vector<std::string>{});
  }
  if (stage == "resolve_strategy_waypoint") {
    bb->set("strategy_waypoint_offsets", std::string("west:bad:0.0"));
    BT::NodeConfiguration config;
    config.blackboard = bb;
    ResolveStrategyWaypoint resolver("resolver", config);
    ASSERT_EQ(resolver.executeTick(), BT::NodeStatus::FAILURE);
  }
  NavigationMetrics metrics;
  if (!early && stage != "resolve_strategy_waypoint") metrics.start();
  const auto before = n1_result_row(bb, metrics);
  CommonResultWriter writer;
  std::string error;
  ASSERT_TRUE(finalize_n1_logging(bb, metrics, writer, path, error)) << error;
  const auto first = lines(path);
  ASSERT_TRUE(finalize_n1_logging(bb, metrics, writer, path, error)) << error;
  EXPECT_EQ(lines(path), first);
  ASSERT_EQ(first.size(), 2u);
  const auto row = n1_result_row(bb, metrics);
  EXPECT_EQ(first[1] + "\n", serialize_common_result(row));
  EXPECT_EQ(row.size(), 35u);
  EXPECT_EQ(row.at("condition"), "MEMORY_ON");
  EXPECT_EQ(row.at("success"), stage.empty() ? "true" : "false");
  EXPECT_EQ(row.at("failure_stage"), stage);
  EXPECT_EQ(row.at("final_goal_nav2_result"), before.at("final_goal_nav2_result"));
  EXPECT_EQ(row.at("waypoint_nav2_result"), before.at("waypoint_nav2_result"));
  EXPECT_EQ(row.at("memory_ids"), stage == "query_memory" ? "N/A" : "M001|M046");
  EXPECT_EQ(row.at("source_memory"), early ? "N/A" : "M001");
  EXPECT_EQ(row.at("retrieved_strategy"), early ? "N/A" : "west");
  EXPECT_EQ(row.at("strategy_applied"), early ? "N/A" : (input.applied ? "true" : "false"));
  EXPECT_EQ(row.at("strategy_waypoint_enabled"), "true");
  EXPECT_EQ(row.at("strategy_waypoint_offsets"),
    stage == "resolve_strategy_waypoint" ? "west:bad:0.0" : "west:-0.25:0.0");
  EXPECT_EQ(row.at("selected_waypoint_x"), input.applied ? "2.250" : "N/A");
  EXPECT_EQ(row.at("selected_waypoint_y"), input.applied ? "-3.000" : "N/A");
  if (early || stage == "resolve_strategy_waypoint") {
    EXPECT_EQ(row.at("navigation_time_s"), "N/A");
    EXPECT_EQ(row.at("distance_m"), "N/A");
    EXPECT_EQ(row.at("replanning_count"), "N/A");
  }
  for (const auto * key : {"min_clearance_m", "context_compliance", "intervention_appropriate"}) {
    EXPECT_EQ(row.at(key), "N/A");
  }
}

INSTANTIATE_TEST_SUITE_P(
  Runs, N1Outcomes, ::testing::Values(
    Outcome{"WaypointSuccess", "", "SUCCEEDED", true},
    Outcome{"DirectSuccess", "", "SUCCEEDED", false},
    Outcome{"WaypointAborted", "navigate_waypoint", "ABORTED", true},
    Outcome{"WaypointRejected", "navigate_waypoint", "REJECTED", true},
    Outcome{"MemoryFailure", "query_memory", "NOT_STARTED", false},
    Outcome{"RecommendationFailure", "get_navigation_recommendation", "NOT_STARTED", false},
    Outcome{"InvalidOffsets", "resolve_strategy_waypoint", "NOT_STARTED", false},
    Outcome{"FinalGoalFailure", "navigate_nav2", "ABORTED", true}),
  [](const ::testing::TestParamInfo<Outcome> & info) { return info.param.name; });

TEST_F(N1Logging, ActualN0AndN1RowsHaveIdentical35FieldHeaders)
{
  NavigationMetrics metrics;
  const auto bb = base_result();
  CommonResultWriter n0_writer, n1_writer;
  std::string error;
  const auto n0_path = directory + "/n0.csv";
  ASSERT_TRUE(n0_writer.write_once(n0_path, n0_reference_row(bb, metrics), error)) << error;
  ASSERT_TRUE(finalize_n1_logging(bb, metrics, n1_writer, path, error)) << error;
  const auto n0 = lines(n0_path), n1 = lines(path);
  ASSERT_EQ(n0.size(), 2u);
  ASSERT_EQ(n1.size(), 2u);
  EXPECT_EQ(n0[0], n1[0]);
  EXPECT_EQ(n1[0] + "\n", common_result_header());
  EXPECT_EQ(std::count(n1[0].begin(), n1[0].end(), ','), 34);
  EXPECT_EQ(common_result_fields().size(), 35u);
}

TEST_F(N1Logging, MetricsRemainContinuousAcrossBothGoals)
{
  NavigationMetrics metrics;
  metrics.observe_odometry(odom(100, 100));
  metrics.observe_plan();
  const auto start = NavigationMetrics::Clock::time_point{};
  metrics.start(start);  // First goal: waypoint.
  metrics.observe_odometry(odom(0, 0));
  metrics.observe_odometry(odom(3, 4));
  metrics.observe_plan();
  metrics.observe_plan();
  metrics.start(start + std::chrono::seconds(2));  // Second goal: no reset.
  metrics.observe_odometry(odom(6, 8));
  metrics.observe_plan();
  EXPECT_FALSE(std::filesystem::exists(path));  // No intermediate row.
  CommonResultWriter writer;
  std::string error;
  const auto bb = base_result();
  ASSERT_TRUE(finalize_n1_logging(bb, metrics, writer, path, error,
    start + std::chrono::seconds(5))) << error;
  metrics.observe_odometry(odom(1000, 1000));
  metrics.observe_plan();
  const auto row = n1_result_row(bb, metrics);
  EXPECT_EQ(row.at("navigation_time_s"), "5.000");
  EXPECT_EQ(row.at("distance_m"), "10.000");
  EXPECT_EQ(row.at("replanning_count"), "2");
  EXPECT_EQ(lines(path).size(), 2u);
}

TEST_F(N1Logging, WriteFailureIsReportedWithoutRetry)
{
  NavigationMetrics metrics;
  CommonResultWriter writer;
  std::string error;
  EXPECT_FALSE(finalize_n1_logging(base_result(), metrics, writer,
    directory + "/missing/result.csv", error));
  EXPECT_NE(error.find("cannot open"), std::string::npos);
  EXPECT_FALSE(finalize_n1_logging(base_result(), metrics, writer, path, error));
  EXPECT_FALSE(std::filesystem::exists(path));
}
}  // namespace
}  // namespace wheelchair_assistive_bt
