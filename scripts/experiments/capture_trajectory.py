"""Map-frame TF observations, sampled at 10 Hz; no goals or DB access."""
import argparse
import json
from pathlib import Path


class CaptureUnavailable(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


class CaptureSampler:
    """Use actual TF timestamps; never relabel stale poses with current clock."""
    def __init__(self):
        self.last_attempt_ns = None
        self.last_pose_ns = None
        self.started = False
        self.waiting_errors = 0
        self.duplicates = 0

    def sample(self, clock_ns, lookup):
        if self.last_attempt_ns is not None and clock_ns - self.last_attempt_ns < 100_000_000:
            return None
        self.last_attempt_ns = clock_ns
        try:
            pose = lookup()
        except CaptureUnavailable as error:
            if not self.started:
                self.waiting_errors += 1
                return None
            return {'t': clock_ns / 1e9, 'capture_error': error.kind,
                    'capture_error_message': str(error)}
        stamp_ns = pose['stamp_ns']
        if stamp_ns <= 0:
            return None
        if clock_ns - stamp_ns > 1_000_000_000:
            if not self.started:
                self.waiting_errors += 1
                return None
            return {'t': clock_ns / 1e9, 'capture_error': 'TF_TIMESTAMP_UNAVAILABLE',
                    'transform_t': stamp_ns / 1e9}
        if self.last_pose_ns is not None and stamp_ns <= self.last_pose_ns:
            self.duplicates += 1
            return None
        self.started = True
        self.last_pose_ns = stamp_ns
        return {'t': stamp_ns / 1e9, 'x': pose['x'], 'y': pose['y'], 'frame': 'map'}


def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.time import Time
    from rclpy.parameter import Parameter
    from tf2_ros import Buffer, TransformListener, TransformException
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stream = args.output.open('x')
    rclpy.init()
    node = Node('experimental_trajectory_capture', parameter_overrides=[
        Parameter('use_sim_time', value=True)])
    buffer = Buffer(node=node)
    listener = TransformListener(buffer, node)
    sampler = CaptureSampler()

    def lookup():
        try:
            # TimePointZero means latest common TF time, not current /clock.
            tf = buffer.lookup_transform('map', 'base_link', Time())
        except TransformException as error:
            raise CaptureUnavailable(type(error).__name__, str(error)) from error
        stamp = tf.header.stamp
        position = tf.transform.translation
        return {'stamp_ns': stamp.sec * 1_000_000_000 + stamp.nanosec,
                'x': position.x, 'y': position.y}

    def sample_tick():
        row = sampler.sample(node.get_clock().now().nanoseconds, lookup)
        if row is not None:
            stream.write(json.dumps(row) + '\n')
            stream.flush()

    # Timer runs on ROS/simulation time; TF callbacks need not precede /clock.
    timer = node.create_timer(0.1, sample_tick, clock=node.get_clock())
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stream.close()
        with args.output.with_suffix('.capture_metadata.json').open('x') as metadata:
            json.dump({'sample_rate_hz': 10, 'sampling_clock': 'ROS_TIMER', 'lookup': 'latest common TF time',
                       'timestamp_source': 'transform.header.stamp', 'use_sim_time': True,
                       'started': sampler.started,
                       'initial_tf_wait_attempts': sampler.waiting_errors,
                       'duplicate_tf_timestamps_not_resampled': sampler.duplicates}, metadata, indent=2)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
