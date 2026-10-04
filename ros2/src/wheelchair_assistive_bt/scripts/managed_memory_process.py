#!/usr/bin/env python3
# Lifecycle entry point only: reuse the existing node classes without modifying memory.
import argparse
import os
import sys
import rclpy
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor, ExternalShutdownException

def run_node(node_factory, executor_factory):
    rclpy.init()
    executor = executor_factory()
    node = None
    normal_shutdown = False
    try:
        node = node_factory()
        executor.add_node(node)
        executor.spin()
        normal_shutdown = True
    except (KeyboardInterrupt, ExternalShutdownException):
        normal_shutdown = True
    finally:
        print('LIFECYCLE cleanup: executor', flush=True)
        executor.shutdown()
        if node is not None:
            print('LIFECYCLE cleanup: node', flush=True)
            node.destroy_node()
        print('LIFECYCLE cleanup: context', flush=True)
        rclpy.try_shutdown()
        backend = getattr(node, 'memory_service', None)
        if backend is not None:
            backend.engine.dispose()
        print('LIFECYCLE cleanup: complete', flush=True)
        if normal_shutdown and backend is not None:
            # The embedding worker hangs in native interpreter finalization even
            # after ROS cleanup (reproduced with no remaining Python frames).
            # Exit this dedicated worker only after ROS and DB cleanup succeed.
            # Exceptions retain their normal nonzero exit and traceback.
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)

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
