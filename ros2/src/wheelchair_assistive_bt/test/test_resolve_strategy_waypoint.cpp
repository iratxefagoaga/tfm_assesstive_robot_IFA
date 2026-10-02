#include <gtest/gtest.h>

// Use the actual production consumer, excluding only its executable entry point.
// No ROS node, service, action client, or navigation process is started.
#define WHEELCHAIR_ASSISTIVE_BT_RESOLVER_TEST
#include "../src/memory_observation_orchestrator.cpp"

namespace wheelchair_assistive_bt
{
namespace
{
struct ResolverCase
{
  const char * name;
  bool enabled;
  const char * strategy;
  const char * offsets;
  bool applied;
  bool invalid;
};

class ResolverContract : public ::testing::TestWithParam<ResolverCase> {};

TEST_P(ResolverContract, ResolvesAndPropagatesConsumerState)
{
  const auto & input = GetParam();
  auto bb = BT::Blackboard::create();
  bb->set("context", std::make_shared<Context>());
  bb->set("retrieved_strategy", std::string(input.strategy));
  bb->set("strategy_waypoint_enabled", input.enabled);
  bb->set("strategy_waypoint_offsets", std::string(input.offsets));

  constexpr double final_goal_yaw = 1.2;
  geometry_msgs::msg::PoseStamped goal;
  goal.header.frame_id = "map";
  goal.pose.position.x = 2.5;
  goal.pose.position.y = -3.0;
  goal.pose.orientation.z = std::sin(final_goal_yaw / 2.0);
  goal.pose.orientation.w = std::cos(final_goal_yaw / 2.0);
  bb->set("final_goal", goal);

  // Sentinels verify that the consumer actively clears stale outputs.
  bb->set("selected_waypoint", goal);
  bb->set("strategy_applied", true);
  bb->set("success", true);
  bb->set("failure_stage", std::string(""));
  bb->set("failure_reason", std::string(""));
  bb->set("waypoint_nav2_result", std::string("SENTINEL"));
  bb->set("final_goal_nav2_result", std::string("NOT_SENT"));

  bool reached_next_consumer = false;
  BT::BehaviorTreeFactory factory;
  factory.registerNodeType<ResolveStrategyWaypoint>("ResolveStrategyWaypoint");
  factory.registerSimpleAction("NextConsumer", [&reached_next_consumer](BT::TreeNode &) {
    reached_next_consumer = true;
    return BT::NodeStatus::SUCCESS;
  });
  auto tree = factory.createTreeFromText(R"(
    <root BTCPP_format="4">
      <BehaviorTree ID="ResolverContract">
        <Sequence>
          <ResolveStrategyWaypoint/>
          <NextConsumer/>
        </Sequence>
      </BehaviorTree>
    </root>)", bb);

  EXPECT_EQ(tree.tickOnce(), input.invalid ? BT::NodeStatus::FAILURE : BT::NodeStatus::SUCCESS);
  EXPECT_EQ(reached_next_consumer, !input.invalid);
  EXPECT_EQ(bb->get<bool>("strategy_applied"), input.applied);
  EXPECT_EQ(bb->get<std::string>("waypoint_nav2_result"), "NOT_APPLIED");
  EXPECT_EQ(bb->get<std::string>("final_goal_nav2_result"), "NOT_SENT");
  EXPECT_EQ(bb->get<geometry_msgs::msg::PoseStamped>("final_goal"), goal);
  const auto selected = bb->get<geometry_msgs::msg::PoseStamped>("selected_waypoint");
  if (input.applied) {
    EXPECT_DOUBLE_EQ(selected.pose.position.x, 2.25);
    EXPECT_DOUBLE_EQ(selected.pose.position.y, -3.0);
    EXPECT_EQ(selected.header.frame_id, "map");
    EXPECT_EQ(selected.pose.orientation, goal.pose.orientation);
    const double selected_yaw = 2.0 * std::atan2(
      selected.pose.orientation.z, selected.pose.orientation.w);
    EXPECT_NEAR(selected_yaw, final_goal_yaw, 1e-12);
  } else {
    EXPECT_EQ(selected, geometry_msgs::msg::PoseStamped{});
  }
  if (input.invalid) {
    EXPECT_FALSE(bb->get<bool>("success"));
    EXPECT_EQ(bb->get<std::string>("failure_stage"), "resolve_strategy_waypoint");
    EXPECT_FALSE(bb->get<std::string>("failure_reason").empty());
  } else {
    EXPECT_TRUE(bb->get<std::string>("failure_stage").empty());
  }
}

INSTANTIATE_TEST_SUITE_P(
  Canonical, ResolverContract,
  ::testing::Values(
    ResolverCase{"Disabled", false, "west", "west:-0.25:0.0", false, false},
    ResolverCase{"Direct", true, "direct", "direct:-0.25:0.0", false, false},
    ResolverCase{"MissingStrategy", true, "west", "central:-0.25:0.0", false, false},
    ResolverCase{"ValidWest", true, "west", "west:-0.25:0.0", true, false},
    ResolverCase{"ZeroOffset", true, "west", "west:0.0:0.0", false, false},
    ResolverCase{"DuplicateStrategy", true, "west", "west:-0.25:0.0,west:-0.5:0.0", false, true},
    ResolverCase{"MalformedDx", true, "west", "west:bad:0.0", false, true},
    ResolverCase{"MalformedDy", true, "west", "west:-0.25:bad", false, true},
    ResolverCase{"NumericSuffix", true, "west", "west:-0.25foo:0.0", false, true},
    ResolverCase{"EmptyStrategy", true, "west", ":-0.25:0.0", false, true}),
  [](const ::testing::TestParamInfo<ResolverCase> & info) { return info.param.name; });
}  // namespace
}  // namespace wheelchair_assistive_bt
