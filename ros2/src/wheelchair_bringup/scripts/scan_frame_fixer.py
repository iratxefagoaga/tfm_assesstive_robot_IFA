#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import LaserScan


class ScanFrameFixer(Node):

    def __init__(self):
        super().__init__("scan_frame_fixer")

        self.publisher = self.create_publisher(
            LaserScan,
            "/scan_fixed",
            10
        )

        self.subscription = self.create_subscription(
            LaserScan,
            "/scan",
            self.scan_callback,
            10
        )

        self.get_logger().info("Scan Frame Fixer iniciado")

    def scan_callback(self, msg: LaserScan):
        msg.header.frame_id = "lidar_link"
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = ScanFrameFixer()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass

    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
