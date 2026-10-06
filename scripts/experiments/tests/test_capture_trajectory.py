from scripts.experiments.capture_trajectory import CaptureSampler, CaptureUnavailable


def pose(stamp):
    return {'stamp_ns': stamp, 'x': 2.0, 'y': -6.0}


def test_clock_ahead_of_tf_preserves_observed_timestamp_and_limits_rate():
    sampler = CaptureSampler()
    assert sampler.sample(1_020_000_000, lambda: pose(1_000_000_000))['t'] == 1.0
    def unexpected_lookup():
        raise AssertionError('sampling each /clock message would regress to 1000 Hz')
    assert sampler.sample(1_021_000_000, unexpected_lookup) is None
    assert sampler.sample(1_120_000_000, lambda: pose(1_100_000_000))['t'] == 1.1


def test_initial_tf_wait_is_distinct_from_capture_error_after_start():
    sampler = CaptureSampler()
    def missing():
        raise CaptureUnavailable('LookupException', 'map absent')
    assert sampler.sample(100_000_000, missing) is None
    assert not sampler.started and sampler.waiting_errors == 1
    assert sampler.sample(200_000_000, lambda: pose(180_000_000))['frame'] == 'map'
    row = sampler.sample(300_000_000, missing)
    assert row['capture_error'] == 'LookupException'
    assert row['capture_error_message'] == 'map absent'


def test_stale_pose_is_not_retimestamped_or_duplicated():
    sampler = CaptureSampler()
    sampler.sample(1_000_000_000, lambda: pose(900_000_000))
    assert sampler.sample(1_100_000_000, lambda: pose(900_000_000)) is None
    assert sampler.sample(2_000_000_000, lambda: pose(900_000_000))['capture_error'] == 'TF_TIMESTAMP_UNAVAILABLE'


def test_new_tf_ahead_of_local_clock_callback_is_real_monotonic_sample():
    sampler = CaptureSampler()
    first = sampler.sample(11_839_000_000, lambda: pose(11_840_000_000))
    second = sampler.sample(11_939_000_000, lambda: pose(11_940_000_000))
    assert first['t'] == 11.840
    assert second['t'] == 11.940
    assert second['t'] > first['t']
    assert 'capture_error' not in second


def test_regressed_transform_timestamp_is_not_output():
    sampler = CaptureSampler()
    sampler.sample(1_000_000_000, lambda: pose(1_000_000_000))
    assert sampler.sample(1_100_000_000, lambda: pose(990_000_000)) is None
