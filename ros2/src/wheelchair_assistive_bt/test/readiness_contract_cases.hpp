#include <gtest/gtest.h>
#include <filesystem>

namespace wheelchair_assistive_bt
{
namespace
{
class ReadinessContract : public ::testing::Test
{
protected:
  using Status = Nav2ReadinessCheck::Status;
  std::vector<std::string> names = required_nav2_nodes();
  Nav2ReadinessCheck::Clock::time_point now{};
  int state = 3;
  bool unavailable = false, pending = false;
  size_t calls = 0, goals = 0;
  std::vector<Nav2ReadinessCheck::Reply> replies;
  rclcpp::Node::SharedPtr node;
  rclcpp_action::Server<NavigateToPose>::SharedPtr server;
  std::unique_ptr<rclcpp::executors::SingleThreadedExecutor> executor;
  BT::Blackboard::Ptr bb;
#ifdef G2E_N0
  std::shared_ptr<ExecutionContext> context;
#else
  std::shared_ptr<Context> context;
#endif
  std::shared_ptr<Nav2ReadinessCheck> check;

  void SetUp() override
  {
    if (!rclcpp::ok()) rclcpp::init(0, nullptr);
    executor = std::make_unique<rclcpp::executors::SingleThreadedExecutor>();
    node = std::make_shared<rclcpp::Node>("readiness_contract_test");
    executor->add_node(node);
    server = rclcpp_action::create_server<NavigateToPose>(node, "/readiness_test_navigate",
      [this](const rclcpp_action::GoalUUID &, std::shared_ptr<const NavigateToPose::Goal>) {
        ++goals;
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
      },
      [](auto) {return rclcpp_action::CancelResponse::ACCEPT;},
      [](auto handle) {handle->succeed(std::make_shared<NavigateToPose::Result>());});
    check = std::make_shared<Nav2ReadinessCheck>(
      [this](const std::string & name, Nav2ReadinessCheck::Reply reply) -> Nav2ReadinessCheck::Cancel {
        ++calls;
        if (pending) replies.push_back(reply);
        else reply(unavailable ? -1 : (name == names.back() ? state : 3),
                   unavailable ? "service unavailable" : "");
        return {};
      }, [this] {return now;});
    bb = BT::Blackboard::create();
#ifdef G2E_N0
    context = std::make_shared<ExecutionContext>();
    bb->set("execution_context", context);
    context->navigate_client = rclcpp_action::create_client<NavigateToPose>(node, "/readiness_test_navigate");
    ASSERT_TRUE(context->navigate_client->wait_for_action_server(std::chrono::seconds(2)));
#else
    context = std::make_shared<Context>();
    bb->set("context", context);
    context->navigate = rclcpp_action::create_client<NavigateToPose>(node, "/readiness_test_navigate");
    ASSERT_TRUE(context->navigate->wait_for_action_server(std::chrono::seconds(2)));
#endif
    context->node = node.get();
    context->readiness = check;
    context->metrics = std::make_shared<NavigationMetrics>();
    for (const auto * key : {"experiment_id", "scenario_id", "run_id", "user_id",
        "location", "task", "goal_label"}) bb->set(key, std::string("fixture"));
    bb->set("success", false);
    bb->set("failure_stage", std::string(""));
    bb->set("failure_reason", std::string(""));
    bb->set("nav2_result", std::string("NOT_STARTED"));
    bb->set("final_goal_nav2_result", std::string("NOT_SENT"));
    bb->set("waypoint_nav2_result", std::string("NOT_APPLIED"));
    bb->set("strategy_applied", false);
    bb->set("strategy_waypoint_enabled", true);
    bb->set("strategy_waypoint_offsets", std::string("west:-0.25:0.0"));
    bb->set("memory_ids", std::vector<std::string>{});
    bb->set("recommendation_result", std::string("NOT_STARTED"));
    bb->set("goal_yaw", 0.4);
    geometry_msgs::msg::PoseStamped goal;
    goal.header.frame_id = "map";
    goal.pose.position.x = 2.5;
    goal.pose.position.y = -3.0;
    goal.pose.orientation.w = 1;
    bb->set("final_goal", goal);
    goal.pose.position.x = 2.25;
    bb->set("selected_waypoint", goal);
  }

  void TearDown() override
  {
    check->reset();
    executor->remove_node(node);
    server.reset();
    context.reset();
    node.reset();
  }
  void initial_pass()
  {
    check->begin(std::chrono::seconds(60));
    ASSERT_EQ(check->poll(), Status::ALLOWED);
    ASSERT_EQ(calls, names.size());
  }
  std::unique_ptr<NavigateNav2> action(const std::string & stage = "final_goal")
  {
    BT::NodeConfiguration config;
    config.blackboard = bb;
    config.input_ports["goal"] = stage == "waypoint" ? "{selected_waypoint}" : "{final_goal}";
#ifndef G2E_N0
    config.input_ports["stage"] = stage;
#endif
    return std::make_unique<NavigateNav2>("navigate", config);
  }
  BT::NodeStatus finish(NavigateNav2 & action)
  {
    auto status = BT::NodeStatus::RUNNING;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (status == BT::NodeStatus::RUNNING && std::chrono::steady_clock::now() < deadline) {
      executor->spin_some();
      status = action.onRunning();
    }
    return status;
  }
  void blocked(NavigateNav2 & action)
  {
    EXPECT_EQ(action.onStart(), BT::NodeStatus::FAILURE);
    EXPECT_EQ(goals, 0u);
    EXPECT_EQ(bb->get<std::string>("final_goal_nav2_result"), "NOT_SENT");
    EXPECT_EQ(bb->get<std::string>("failure_stage"), "readiness");
    EXPECT_FALSE(bb->get<bool>("success"));
    EXPECT_EQ(context->metrics->time_s(), "N/A");
  }
  void finalize()
  {
#ifdef G2E_N0
    finalize_n0_experiment(bb);
#else
    finalize_n1_experiment(bb);
#endif
  }
  ResultRow row()
  {
#ifdef G2E_N0
    return n0_result_row(bb, *context->metrics);
#else
    return n1_result_row(bb, *context->metrics);
#endif
  }
};

TEST_F(ReadinessContract, T1AllCanonicalActivePermitsGoal)
{
  auto nav = action();
  ASSERT_EQ(nav->onStart(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(finish(*nav), BT::NodeStatus::SUCCESS);
  EXPECT_EQ(goals, 1u);
  EXPECT_EQ(calls, names.size());
}
TEST_F(ReadinessContract, T2InitialPassThenInactiveBlocks)
{
  initial_pass(); state = 2;
  auto nav = action(); blocked(*nav);
  EXPECT_EQ(calls, 2 * names.size());
}
TEST_F(ReadinessContract, T3TimeoutBlocks)
{
  initial_pass(); pending = true;
  auto nav = action();
  EXPECT_EQ(nav->onStart(), BT::NodeStatus::RUNNING);
  now += std::chrono::seconds(61);
  EXPECT_EQ(nav->onRunning(), BT::NodeStatus::FAILURE);
  EXPECT_EQ(goals, 0u);
  EXPECT_EQ(bb->get<std::string>("failure_stage"), "readiness");
  EXPECT_NE(bb->get<std::string>("failure_reason").find("timeout"), std::string::npos);
}
TEST_F(ReadinessContract, T4TransientServiceUnavailableRetriesUntilReady)
{
  unavailable = true;
  auto nav = action();
  EXPECT_EQ(nav->onStart(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(goals, 0u);
  EXPECT_EQ(bb->get<std::string>("final_goal_nav2_result"), "NOT_SENT");
  unavailable = false;
  EXPECT_EQ(finish(*nav), BT::NodeStatus::SUCCESS);
  EXPECT_EQ(goals, 1u);
  EXPECT_EQ(calls, 3 * names.size());
}
#ifdef G2E_N0
TEST_F(ReadinessContract, T8N0MemoryFreeEvenOnFailure)
{
  state = 2;
  auto nav = action(); blocked(*nav);
  for (const auto & service : node->get_service_names_and_types()) {
    EXPECT_EQ(service.first.find("/memory/"), std::string::npos);
  }
  EXPECT_EQ(row().at("source_memory"), "N/A");
}
#else
TEST_F(ReadinessContract, T5WaypointPermitted)
{
  bb->set("strategy_applied", true);
  auto nav = action("waypoint");
  EXPECT_EQ(nav->onStart(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(finish(*nav), BT::NodeStatus::SUCCESS);
  EXPECT_EQ(goals, 1u);
  EXPECT_EQ(bb->get<std::string>("waypoint_nav2_result"), "SUCCEEDED");
}
TEST_F(ReadinessContract, T6WaypointSucceededThenFinalBlocked)
{
  bb->set("strategy_applied", true);
  auto waypoint = action("waypoint");
  EXPECT_EQ(waypoint->onStart(), BT::NodeStatus::RUNNING);
  ASSERT_EQ(finish(*waypoint), BT::NodeStatus::SUCCESS);
  state = 2;
  auto final = action();
  EXPECT_EQ(final->onStart(), BT::NodeStatus::FAILURE);
  EXPECT_EQ(goals, 1u);
  EXPECT_EQ(bb->get<std::string>("waypoint_nav2_result"), "SUCCEEDED");
  EXPECT_EQ(bb->get<std::string>("final_goal_nav2_result"), "NOT_SENT");
  EXPECT_EQ(bb->get<std::string>("failure_stage"), "readiness");
  finalize();
  EXPECT_EQ(row().at("waypoint_nav2_result"), "SUCCEEDED");
}
TEST_F(ReadinessContract, T7WaypointThenFreshFinalPermitted)
{
  bb->set("strategy_applied", true);
  auto waypoint = action("waypoint");
  EXPECT_EQ(waypoint->onStart(), BT::NodeStatus::RUNNING);
  ASSERT_EQ(finish(*waypoint), BT::NodeStatus::SUCCESS);
  auto final = action();
  EXPECT_EQ(final->onStart(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(finish(*final), BT::NodeStatus::SUCCESS);
  EXPECT_EQ(goals, 2u);
  EXPECT_EQ(calls, 2 * names.size());
}
TEST_F(ReadinessContract, WaypointReadinessFailureLeavesBothNotSent)
{
  bb->set("strategy_applied", true); state = 2;
  auto waypoint = action("waypoint"); blocked(*waypoint);
  EXPECT_EQ(bb->get<std::string>("waypoint_nav2_result"), "NOT_SENT");
}
#endif
TEST_F(ReadinessContract, T9FinalizeAndCsvExactlyOnce)
{
  state = 2;
  auto nav = action(); blocked(*nav);
  finalize(); finalize();
  EXPECT_EQ(bb->get<int>("finalization_count"), 1);
  EXPECT_EQ(bb->get<std::string>("failure_stage"), "readiness");
  char directory[] = "/tmp/g2e_readiness_XXXXXX";
  ASSERT_NE(mkdtemp(directory), nullptr);
  const auto path = std::string(directory) + "/result.csv";
  CommonResultWriter writer;
  std::string error;
  ASSERT_TRUE(writer.write_once(path, row(), error)) << error;
  ASSERT_TRUE(writer.write_once(path, row(), error)) << error;
  std::ifstream input(path);
  std::string line; size_t lines = 0;
  while (std::getline(input, line)) ++lines;
  EXPECT_EQ(lines, 2u);
  EXPECT_EQ(common_result_fields().size(), 35u);
  EXPECT_EQ(row().at("final_goal_nav2_result"), "NOT_SENT");
  EXPECT_EQ(row().at("failure_stage"), "readiness");
  std::filesystem::remove_all(directory);
}
TEST_F(ReadinessContract, T10LateRepliesCannotReviveOrFinalizeAgain)
{
  pending = true;
  auto nav = action();
  EXPECT_EQ(nav->onStart(), BT::NodeStatus::RUNNING);
  now += std::chrono::seconds(61);
  EXPECT_EQ(nav->onRunning(), BT::NodeStatus::FAILURE);
  finalize();
  const auto before = row();
  for (const auto & reply : replies) reply(3, "");
  executor->spin_some();
  EXPECT_EQ(check->poll(), Status::DENIED);
  EXPECT_EQ(goals, 0u);
  EXPECT_EQ(bb->get<int>("finalization_count"), 1);
  EXPECT_EQ(row().at("failure_stage"), before.at("failure_stage"));
}
TEST_F(ReadinessContract, T11ConsecutiveRoundsNeverReusePass)
{
  initial_pass(); state = 2;
  check->begin(std::chrono::seconds(60));
  EXPECT_EQ(check->poll(), Status::DENIED);
  EXPECT_EQ(calls, 2 * names.size());
}
TEST_F(ReadinessContract, T12AnyNonActiveStateFailsClosed)
{
  for (int id : {0, 1, 2, 4, 10}) {
    state = id;
    check->begin(std::chrono::seconds(60));
    EXPECT_EQ(check->poll(), Status::DENIED) << id;
  }
}
TEST_F(ReadinessContract, OldRoundRepliesCannotAuthorizeNewRound)
{
  pending = true;
  check->begin(std::chrono::seconds(60));
  const auto old = replies; replies.clear();
  check->begin(std::chrono::seconds(60));
  for (const auto & reply : old) reply(3, "");
  EXPECT_EQ(check->poll(), Status::CHECKING);
  for (const auto & reply : replies) reply(2, "");
  EXPECT_EQ(check->poll(), Status::DENIED);
}
TEST_F(ReadinessContract, ResponsesAfterDeadlineFailWithoutPriorPoll)
{
  pending = true;
  check->begin(std::chrono::seconds(60));
  now += std::chrono::seconds(61);
  for (const auto & reply : replies) reply(3, "");
  EXPECT_EQ(check->poll(), Status::DENIED);
}
TEST_F(ReadinessContract, RealGetStateTransportUsesAllRequiredServices)
{
  using Service = lifecycle_msgs::srv::GetState;
  std::vector<rclcpp::Service<Service>::SharedPtr> services;
  for (const auto & name : names) {
    services.push_back(node->create_service<Service>("/" + name + "/get_state",
      [this, name](const Service::Request::SharedPtr, Service::Response::SharedPtr response) {
        response->current_state.id = name == names.back() ? state : 3;
      }));
  }
  Nav2ReadinessCheck actual(node.get());
  actual.begin(std::chrono::seconds(2));
  const auto limit = std::chrono::steady_clock::now() + std::chrono::seconds(3);
  while (actual.poll() == Status::CHECKING && std::chrono::steady_clock::now() < limit) {
    executor->spin_some();
  }
  ASSERT_EQ(actual.poll(), Status::ALLOWED) << actual.reason();
  state = 2;
  actual.begin(std::chrono::seconds(2));
  while (actual.poll() == Status::CHECKING && std::chrono::steady_clock::now() < limit) {
    executor->spin_some();
  }
  EXPECT_EQ(actual.poll(), Status::DENIED);
  EXPECT_NE(actual.reason().find(names.back()), std::string::npos);
}

TEST_F(ReadinessContract, ErrorResponseFailsClosed)
{
  Nav2ReadinessCheck error_check([](const std::string &, Nav2ReadinessCheck::Reply reply) {
    reply(-1, "controlled backend error");
    return Nav2ReadinessCheck::Cancel{};
  });
  error_check.begin(std::chrono::seconds(60));
  EXPECT_EQ(error_check.poll(), Status::DENIED);
}
}  // namespace
}  // namespace wheelchair_assistive_bt
