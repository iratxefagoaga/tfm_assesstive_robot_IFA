#!/usr/bin/env python3
# Lifecycle entry point only: reuse the existing node classes without modifying memory.
import argparse
import rclpy
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor, ExternalShutdownException

def run_node(node_factory, executor_factory):
    rclpy.init()
    executor = executor_factory()
    node = None
    try:
        node = node_factory()
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        print('LIFECYCLE cleanup: executor', flush=True)
        executor.shutdown()
        if node is not None:
            print('LIFECYCLE cleanup: node', flush=True)
            node.destroy_node()
        print('LIFECYCLE cleanup: context', flush=True)
        rclpy.try_shutdown()
        print('LIFECYCLE cleanup: complete', flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('role', choices=['memory', 'recommendation'])
    args, _ = parser.parse_known_args()
    if args.role == 'memory':
        from wheelchair_memory.memory_node import MemoryNode
        run_node(MemoryNode, SingleThreadedExecutor)
    else:
        from wheelchair_memory.navigation_memory_node import NavigationMemoryNode
        run_node(NavigationMemoryNode, lambda: MultiThreadedExecutor(num_threads=2))

if __name__ == '__main__':
    main()
