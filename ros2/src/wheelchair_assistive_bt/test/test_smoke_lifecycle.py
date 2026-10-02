import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from rclpy.executors import ExternalShutdownException

def load(name):
    path = Path(__file__).parents[1] / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

ready = load('wait_for_smoke_ready')
managed = load('managed_memory_process')

class Readiness(unittest.TestCase):
    def test_canonical_list_matches_pre_goal_resource(self):
        from ament_index_python.packages import get_package_share_directory
        resource = Path(get_package_share_directory('wheelchair_navigation')) / 'config/required_nav2_nodes.txt'
        self.assertEqual(ready.NAV_NODES, tuple(resource.read_text().split()))
        header = Path(__file__).parents[1] / 'include/wheelchair_assistive_bt/nav2_readiness.hpp'
        self.assertIn('"/config/required_nav2_nodes.txt"', header.read_text())
        self.assertNotIn('"map_server"', header.read_text())
        launch = Path(get_package_share_directory('wheelchair_navigation')) / 'launch/navigation.launch.py'
        self.assertIn('"required_nav2_nodes.txt"', launch.read_text())
        self.assertIn('"node_names": required_nodes', launch.read_text())

    def test_all_required_active(self):
        self.assertTrue(ready.all_active(dict.fromkeys(ready.NAV_NODES, 3)))
    def test_missing_node_blocks(self):
        states = dict.fromkeys(ready.NAV_NODES, 3)
        del states['map_server']
        self.assertFalse(ready.all_active(states))
    def test_inactive_node_blocks(self):
        states = dict.fromkeys(ready.NAV_NODES, 3)
        states['planner_server'] = 2
        self.assertFalse(ready.all_active(states))

class Shutdown(unittest.TestCase):
    def check_exit(self, exception):
        executor, node = MagicMock(), MagicMock()
        executor.spin.side_effect = exception
        with patch.object(managed.rclpy, 'init'), patch.object(managed.rclpy, 'try_shutdown') as stop:
            managed.run_node(lambda: node, lambda: executor)
            executor.shutdown.assert_called_once()
            node.destroy_node.assert_called_once()
            stop.assert_called_once()
    def test_normal(self): self.check_exit(None)
    def test_sigint(self): self.check_exit(KeyboardInterrupt())
    def test_external_shutdown(self): self.check_exit(ExternalShutdownException())
    def test_failure_is_not_hidden(self):
        with self.assertRaises(RuntimeError):
            self.check_exit(RuntimeError('real failure'))

if __name__ == '__main__':
    unittest.main()
