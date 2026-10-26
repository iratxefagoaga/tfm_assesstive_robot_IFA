import unittest
from diagnose import stage,summarize_log,vertical_interval,load_database_env,existing_memory_database,verify_sensor_overlay
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import json
import hashlib
from types import SimpleNamespace
from unittest.mock import patch
from prepare_sensor_candidate import masked_candidate,collision_signature
from validate_sensor import summarize
from truth_observer import wheelchair_pose
from analyze_localization import compare
from navigation_scan_filter import filtered_ranges
from scan_health import ScanHealth
from physical_acceptance import assess
from release_integrity import check_files,mission_lock
from navigation_cancellation import ActiveGoals
from arrival_reference import reference

class DiagnosisTests(unittest.TestCase):
    def test_cancelled_outer_goal_waits_for_controller_to_stop(self):
        states=ActiveGoals();states.update('/navigate_to_pose',[('a',5)]);states.update('/follow_path',[('b',3)])
        self.assertFalse(states.complete(['a']));states.update('/follow_path',[('b',5)]);self.assertTrue(states.complete(['a']))
    def test_aborted_bridge_is_never_a_clean_shutdown(self):
        self.assertEqual(summarize_log('process has died [pid 9, exit code -6, cmd bridge]')['abnormal_exit'],1)
    def test_overlapping_missions_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'lock'
            with mission_lock(path):
                with self.assertRaises(RuntimeError):
                    with mission_lock(path):pass
            with mission_lock(path):pass
    def scan(self,stamp=1):
        import math
        return SimpleNamespace(angle_min=-math.pi,angle_max=math.pi,angle_increment=2*math.pi/719,range_min=.12,range_max=12.,ranges=[2.]*720,header=SimpleNamespace(stamp=SimpleNamespace(sec=stamp,nanosec=0)))
    def accepted_row(self):
        return {'result':[{'success':'true','waypoint_nav2_result':'SUCCEEDED','final_goal_nav2_result':'SUCCEEDED'}],'cleanup_ok':True,'categories':{},'physical_pose_samples':100,'physical_pose_frame':'world/default','physical_pose_entity':'wheelchair','physical_pose_reference':'nav2_success_observed','physical_pose_age_s':.1,'physical_final_position':{'x':1,'y':-9},'physical_final_orientation':{'w':1},'physical_arrival_position':{'x':1,'y':-9},'physical_arrival_orientation':{'w':1}}
    def test_arrival_reference_does_not_use_shutdown_duration(self):
        poses=[{'wall_monotonic':9.9,'position':{'x':1}}, {'wall_monotonic':11,'position':{'x':99}}]
        result=reference(poses,[{'kind':'navigation_status','wall_monotonic':10,'goals':[{'id':'final','created':5,'status':4}]}])
        self.assertAlmostEqual(result['age_s'],.1);self.assertEqual(result['pose']['position']['x'],1)
    def test_waypoint_success_does_not_replace_unfinished_final(self):
        events=[{'kind':'navigation_status','wall_monotonic':10,'goals':[{'id':'waypoint','created':1,'status':4},{'id':'final','created':5,'status':2}]}]
        self.assertIsNone(reference([{'wall_monotonic':9}],events))
    def test_lidar_loss_and_repeated_timestamps_do_not_refresh_health(self):
        health=ScanHealth(0);self.assertIsNone(health.observe(self.scan(),.1));self.assertIsNone(health.observe(self.scan(),.8))
        self.assertEqual(health.fault(1.2),'scan_stale')
    def test_lidar_clock_regression_and_broken_schema_fail_closed(self):
        health=ScanHealth(0);health.observe(self.scan(2),.1);self.assertEqual(health.observe(self.scan(1),.2),'scan_clock_regressed')
        message=self.scan();message.ranges=[];self.assertEqual(ScanHealth(0).observe(message,.1),'invalid_scan_schema')
    def test_startup_without_scan_has_bounded_deadline(self):
        self.assertIsNone(ScanHealth(0).fault(119));self.assertEqual(ScanHealth(0).fault(121),'scan_startup_missing')
    def test_physical_acceptance_rejects_stale_or_missing_measurement(self):
        row=self.accepted_row();self.assertTrue(assess(row,'memory')['accepted']);row['physical_pose_age_s']=3
        self.assertFalse(assess(row,'memory')['accepted']);del row['physical_final_orientation'];self.assertIn('invalid_truth_pose',assess(row,'memory')['reasons'])
    def test_missing_quaternion_is_not_replaced_by_identity(self):
        row=self.accepted_row();row['physical_final_orientation']={};self.assertIn('invalid_truth_pose',assess(row,'memory')['reasons'])
        row['physical_final_orientation']={'z':1};self.assertIn('settled_pose_outside_tolerance',assess(row,'memory')['reasons'])
    def test_successful_final_does_not_hide_failed_waypoint(self):
        row=self.accepted_row();row['result'][0]['waypoint_nav2_result']='ABORTED';self.assertFalse(assess(row,'memory')['accepted'])
    def test_release_integrity_rejects_source_or_profile_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'artifact';p.write_text('tested');expected={'artifact':hashlib.sha256(p.read_bytes()).hexdigest()};check_files(root,expected)
            p.write_text('changed')
            with self.assertRaises(RuntimeError):check_files(root,expected)
    def test_self_filter_does_not_make_occluded_obstacles_visible(self):
        import math
        result=filtered_ranges([.3],math.pi,0,.12,12)
        self.assertTrue(math.isnan(result[0]))
        self.assertEqual(filtered_ranges([.15,2.0],0,0,.12,12),[.15,2.0])
    def test_pose_comparison_aligns_known_spawn_and_rejects_stale_samples(self):
        truth=[{'stamp':{'sec':'2'},'position':{'x':1,'y':-9},'orientation':{'w':1}}]
        odom=[{'kind':'odom','stamp':2.02,'x':1,'y':0,'q':[0,0,0,1]}, {'kind':'odom','stamp':3.,'x':99,'y':99,'q':[0,0,0,1]}]
        result=compare(truth,odom,'odom');self.assertEqual(result['matched_samples'],1);self.assertEqual(result['rejected_stale_samples'],1)
        self.assertEqual(result['last_pair']['position_error_m'],0)
    def test_amcl_comparison_does_not_apply_spawn_twice(self):
        truth=[{'stamp':{'sec':'2'},'position':{'x':1,'y':-9},'orientation':{'w':1}}]
        result=compare(truth,[{'kind':'amcl','stamp':2,'x':1,'y':-9,'q':[0,0,0,1]}],'amcl')
        self.assertEqual(result['last_pair']['position_error_m'],0)
    def test_truth_uses_world_robot_not_other_entity(self):
        self.assertIsNone(wheelchair_pose({'pose':[{'name':'park'}]}))
        result=wheelchair_pose({'header':{'stamp':{'sec':'3'}},'pose':[{'name':'park','position':{'x':100}}, {'name':'wheelchair','position':{'x':1,'y':-9}}]})
        self.assertEqual(result['position'],{'x':1,'y':-9});self.assertEqual(result['stamp'],{'sec':'3'})
    def test_overlay_rejects_candidate_changed_after_sensor_validation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);model=root/'share/wheelchair_gazebo/models/wheelchair/model.sdf';model.parent.mkdir(parents=True);model.write_text('original candidate')
            (root/'overlay_manifest.json').write_text(json.dumps({'status':'ISOLATED_DIAGNOSTIC_OVERLAY','candidate_sha256':hashlib.sha256(model.read_bytes()).hexdigest()}))
            verify_sensor_overlay(root);model.write_text('changed candidate')
            with self.assertRaises(RuntimeError):verify_sensor_overlay(root)
    def test_sensor_summary_does_not_count_missing_or_invalid_ranges(self):
        data={'scans':[{'ranges':[None,.1,.245,3.,13.],'range_min':.12,'range_max':12.}], 'odometry':[[0,0,0],[.03,0,0]]}
        result=summarize(data)
        self.assertEqual(result['near_hits_max'],1);self.assertEqual(result['far_hits_min'],1)
        self.assertEqual(result['max_odom_translation_m'],.03)
    def test_failed_waypoint_never_accepts_sent_final(self):
        with self.assertRaises(ValueError):stage({'waypoint_nav2_result':'ABORTED','final_goal_nav2_result':'SUCCEEDED'})
    def test_separate_final_failure(self):
        self.assertEqual(stage({'waypoint_nav2_result':'SUCCEEDED','final_goal_nav2_result':'ABORTED'}),'final')
    def test_multiple_diagnostics_not_single_causal_label(self):
        counts=summarize_log('Controller patience exceeded\nFailed to create plan\nGoal failed')
        self.assertEqual(counts['control_patience'],1);self.assertEqual(counts['planning'],1)
        self.assertEqual(counts['readiness'],0)
    def test_low_visual_vs_sensor_plane(self):
        link=ET.fromstring('<link><pose>0 0 0.1 0 0 0</pose><visual><geometry><box><size>30 0.3 0.2</size></box></geometry></visual></link>')
        lo,hi=vertical_interval(link,link.find('visual/geometry'))
        self.assertEqual((lo,hi),(0.,.2));self.assertFalse(lo<=.92<=hi)
    def test_unknown_abortion_keeps_no_invented_reason(self):
        counts=summarize_log('Goal failed')
        self.assertEqual(counts['goal_abort'],1);self.assertEqual(counts['control_patience'],0);self.assertEqual(counts['planning'],0)
    def test_acknowledgement_timeout_is_detected_separately(self):
        c=summarize_log('Timed out while waiting for action server to acknowledge goal request for compute_path_to_pose')
        self.assertEqual(c['action_ack_timeout'],1);self.assertEqual(c['planning'],0)
    def test_readiness_response_failure_is_infrastructure_failure(self):
        self.assertEqual(summarize_log('readiness response failed: /map_server/get_state')['readiness'],1)
    def test_private_file_is_data_not_shell_code(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'private';p.write_text('export MEMORY_DB_NAME="test db"\nTOKEN=unused\nPOSTGRES_USER=legacy\n')
            env=load_database_env(p,{})
            self.assertEqual(env,{'MEMORY_DB_NAME':'test db'})
            env=load_database_env(p,{},postgres_aliases=True)
            self.assertEqual(env['MEMORY_DB_USER'],'legacy');self.assertNotIn('TOKEN',env)
    def test_cleanup_escalation_is_not_clean_termination(self):
        c=summarize_log("failed to terminate, escalating to 'SIGKILL'")
        self.assertGreater(c['cleanup_escalation'],0)
    def test_candidate_only_masks_visuals_and_keeps_collisions(self):
        original=ET.fromstring('<sdf><model><link name="lidar_link"><sensor type="gpu_lidar"><ray><range><min>0.12</min><max>12</max></range></ray></sensor></link><link><visual><geometry><box><size>1 1 1</size></box></geometry></visual><collision><geometry><box><size>1 1 1</size></box></geometry></collision></link></model></sdf>')
        before=ET.tostring(original);candidate=masked_candidate(original)
        self.assertEqual(collision_signature(original),collision_signature(candidate));self.assertEqual(ET.tostring(original),before)
        self.assertEqual(candidate.findtext('.//visibility_mask'),'4294967294')
        self.assertEqual(candidate.findtext('.//visibility_flags'),'1')
    def test_original_database_is_stopped_again_after_diagnostic_error(self):
        info=[{'State':{'Running':False},'Config':{'Env':['POSTGRES_USER=test','POSTGRES_PASSWORD=fixture','POSTGRES_DB=memory']},'HostConfig':{'PortBindings':{'5432/tcp':[{'HostPort':'5433'}]}}}]
        def command(argv,**kwargs):
            return SimpleNamespace(returncode=0,stdout=json.dumps(info) if argv[1]=='inspect' else '')
        with tempfile.TemporaryDirectory() as d,patch('diagnose.subprocess.run',side_effect=command) as run:
            with self.assertRaises(RuntimeError):
                with existing_memory_database(Path(d)) as env:
                    self.assertEqual(env['MEMORY_DB_NAME'],'memory');raise RuntimeError('fixture failure')
            calls=[c.args[0] for c in run.call_args_list]
            self.assertIn(['docker','kill','--signal=SIGINT','tfm_memory_postgres'],calls)
            self.assertNotIn(['docker','rm','tfm_memory_postgres'],calls)

if __name__=='__main__':unittest.main()
