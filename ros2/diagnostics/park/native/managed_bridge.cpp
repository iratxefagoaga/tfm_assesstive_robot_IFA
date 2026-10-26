// Local lifecycle adapter using the installed ros_gz_bridge public/protected API.
// Converters and transport behavior remain in the installed library.
#include <csignal>
#include <chrono>
#include <iostream>
#include <memory>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <ros_gz_bridge/ros_gz_bridge.hpp>
namespace { volatile std::sig_atomic_t stopping=0; void stop(int) { stopping=1; } }
class ManagedBridge final : public ros_gz_bridge::RosGzBridge {
public:
  explicit ManagedBridge(const rclcpp::NodeOptions & options):RosGzBridge(options) {}
  void close_transport() {
    if (heartbeat_timer_) heartbeat_timer_->cancel();
    handles_.clear(); services_.clear(); gz_node_.reset();
  }
};
int main(int argc,char ** argv) {
  std::string kind;
  for (int i=1;i<argc;++i) {
    std::string argument(argv[i]);
    if (argument.rfind("--bridge-kind=",0)==0) kind=argument.substr(14);
  }
  if (kind!="core" && kind!="navigation_scan") { std::cerr<<"Expected bridge kind\n"; return 2; }
  rclcpp::init(argc,argv,rclcpp::InitOptions(),rclcpp::SignalHandlerOptions::None);
  std::signal(SIGINT,stop); std::signal(SIGTERM,stop);
  try {
    rclcpp::NodeOptions options; options.arguments({"--ros-args","-r","__node:=park_bridge_"+kind});
    auto node=std::make_shared<ManagedBridge>(options);
    auto add=[&](const std::string & topic,const std::string & ros,const std::string & gz,ros_gz_bridge::BridgeDirection direction) {
      ros_gz_bridge::BridgeConfig config; config.ros_topic_name=topic; config.gz_topic_name=topic;
      config.ros_type_name=ros; config.gz_type_name=gz; config.direction=direction; node->add_bridge(config);
    };
    using D=ros_gz_bridge::BridgeDirection;
    if (kind=="navigation_scan") add("/navigation_scan","sensor_msgs/msg/LaserScan","gz.msgs.LaserScan",D::GZ_TO_ROS);
    else {
      add("/clock","rosgraph_msgs/msg/Clock","gz.msgs.Clock",D::GZ_TO_ROS);
      add("/cmd_vel","geometry_msgs/msg/Twist","gz.msgs.Twist",D::ROS_TO_GZ);
      add("/odom","nav_msgs/msg/Odometry","gz.msgs.Odometry",D::GZ_TO_ROS);
      add("/tf","tf2_msgs/msg/TFMessage","gz.msgs.Pose_V",D::GZ_TO_ROS);
      add("/joint_states","sensor_msgs/msg/JointState","gz.msgs.Model",D::GZ_TO_ROS);
      add("/scan","sensor_msgs/msg/LaserScan","gz.msgs.LaserScan",D::GZ_TO_ROS);
    }
    rclcpp::executors::SingleThreadedExecutor executor; executor.add_node(node);
    while (!stopping) executor.spin_once(std::chrono::milliseconds(20));
    executor.remove_node(node);
    // Keep ROS valid while Gazebo callbacks and subscriptions are destroyed.
    node->close_transport(); node.reset(); rclcpp::shutdown();
    std::cout<<"CLEAN_BRIDGE_SHUTDOWN "<<kind<<std::endl; return 0;
  } catch (const std::exception & error) {
    std::cerr<<"BRIDGE_FAILURE: "<<error.what()<<std::endl; rclcpp::shutdown(); return 2;
  }
}
