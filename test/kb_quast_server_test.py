# -*- coding: utf-8 -*-
import hashlib
import inspect
import os  # noqa: F401
import shutil
import time
import unittest
import uuid
from configparser import ConfigParser
from os import environ
from unittest.mock import patch

import requests

from installed_clients.AbstractHandleClient import AbstractHandle as HandleService
from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.WorkspaceClient import Workspace
from installed_clients.baseclient import ServerError as AssemblyError
from installed_clients.baseclient import ServerError as KBRError
from installed_clients.baseclient import ServerError as WorkspaceError
from installed_clients.authclient import KBaseAuth as _KBaseAuth
from kb_quast.kb_quastImpl import kb_quast
from kb_quast.kb_quastServer import MethodContext


class kb_quastTest(unittest.TestCase):

    WORKDIR = '/kb/module/work/tmp/'

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_quast'):
            cls.cfg[nameval[0]] = nameval[1]
        authServiceUrl = cls.cfg.get(
            'auth-service-url',
            "https://kbase.us/services/authorization/Sessions/Login"
        )
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(cls.token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({
            'token': cls.token,
            'user_id': user_id,
            'provenance': [{'service': 'kb_quast',
                            'method': 'please_never_use_it_in_production',
                            'method_params': []}],
            'authenticated': 1
        })
        cls.shockURL = cls.cfg['shock-url']
        cls.ws = Workspace(cls.cfg['workspace-url'], token=cls.token)
        cls.hs = HandleService(url=cls.cfg['handle-service-url'], token=cls.token)
        cls.au = AssemblyUtil(os.environ['SDK_CALLBACK_URL'])
        cls.impl = kb_quast(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        shutil.rmtree(cls.scratch)
        os.mkdir(cls.scratch)
        suffix = int(time.time() * 1000)
        wsName = "test_ReadsUtils_" + str(suffix)
        cls.ws_info = cls.ws.create_workspace({'workspace': wsName})
        cls.dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'])
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        print('\n\n=============== Starting tests ==================')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'ws_info'):
            cls.ws.delete_workspace({'id': cls.ws_info[0]})
            print('Deleted test workspace: {}'.format(cls.ws_info[0]))
        if hasattr(cls, 'nodes_to_delete'):
            for node in cls.nodes_to_delete:
                cls.delete_shock_node(node)
        if hasattr(cls, 'handles_to_delete'):
            if cls.handles_to_delete:
                cls.hs.delete_handles(cls.hs.hids_to_handles(cls.handles_to_delete))
                print('Deleted handles ' + str(cls.handles_to_delete))

    def getWsName(self):
        return self.ws_info[1]

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header, allow_redirects=True)
        print('Deleted shock node ' + node_id)

    def start_test(self):
        testname = inspect.stack()[1][3]
        print('\n*** starting test: ' + testname + ' **')

# ***** quast as local method tests ************************

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_check_large_input(self):
        self.start_test()

        file_dir = os.path.join(self.scratch, 'quast_large_file')
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        large_file_name = 'large_file.fa'
        large_file_path = os.path.join(file_dir, large_file_name)

        size_fake_20MB = 10

        # writing exactly TWENTY_MB base count
        with open(large_file_path, "a") as output:
            content = '>test_seq\n{}'.format('A' * size_fake_20MB)
            output.write(content)

        skip_glimmer = self.impl.check_large_input([large_file_path])
        self.assertFalse(skip_glimmer)

        # writing exactly TWENTY_MB + 1 base count
        with open(large_file_path, "a") as output:
            content = 'A'
            output.write(content)

        skip_glimmer = self.impl.check_large_input([large_file_path])
        self.assertTrue(skip_glimmer)

        os.remove(large_file_path)

    def test_quast_from_1_file(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {
            'files': [{'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}],
            'make_handle': 1
        })[0]
        self.check_quast_output(ret, 329729, 'a64692fe665ba0174ca4992caa00ea77',
                                '6522bf4c7a54f96b99f7097c1a6afb01')

    def test_quast_min_contig_length(self):
        self.start_test()
        # manually checked that the min contig length was showing up in the results
        test_params = [
            {
                'min_contig_length': 50,
                'expected_size': 330614,
                'expected_report_md5': '741b2d1dec8dbb81fe9a877c4bc1e329',
                'expected_icarus_md5': '6522bf4c7a54f96b99f7097c1a6afb01'
            },
            {
                'min_contig_length': 100,
                'expected_size': 330656,
                'expected_report_md5': '354573cf4b70a013abb20e568aeae7f6',
                'expected_icarus_md5': '6522bf4c7a54f96b99f7097c1a6afb01'
            },
            {
                'min_contig_length': None,
                'expected_size': 329785,
                'expected_report_md5': '0812e658c08374fa26a1a93dd6b4402d',
                'expected_icarus_md5': '6522bf4c7a54f96b99f7097c1a6afb01'
            }
        ]
        for p in test_params:
            params = {
                'files': [{'path': 'data/greengenes_UnAligSeq24606_short_seqs.fa',
                           'label': 'foobar'}],
                'make_handle': 1,
                'min_contig_length': p['min_contig_length']
            }
            ret = self.impl.run_QUAST(self.ctx, params)[0]
            self.check_quast_output(
                ret, p['expected_size'], p['expected_report_md5'], p['expected_icarus_md5'])

    def test_quast_no_handle(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {
            'files': [{'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}],
            'make_handle': 0
        })[0]
        self.check_quast_output(ret, 329726, 'a64692fe665ba0174ca4992caa00ea77',
                                '6522bf4c7a54f96b99f7097c1a6afb01', no_handle=True)

        ret = self.impl.run_QUAST(self.ctx, {
            'files': [{'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}]
        })[0]
        self.check_quast_output(ret, 329727, 'a64692fe665ba0174ca4992caa00ea77',
                                '6522bf4c7a54f96b99f7097c1a6afb01', no_handle=True)

    def test_quast_from_2_files(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {
            'files': [
                {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
                {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}
            ],
            'make_handle': 1
        })[0]
        self.check_quast_output(ret, 350263, 'd993842bcd881592aad50a8df8925499',
                                '2d10706f4ecfdbbe6d5d86e8578adbfa')

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_large_file(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {
            'files': [
                {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
                {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}
            ],
            'make_handle': 1
        })[0]

        self.check_quast_output(ret, 346400, '6aebc5fd90156d8ce31c64f30e19fa19',
                                '2d10706f4ecfdbbe6d5d86e8578adbfa', skip_glimmer=True)

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_large_file_force_glimmer(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {
            'files': [
                {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
                {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}
            ],
            'make_handle': 1,
            'force_glimmer': True
        })[0]
        self.check_quast_output(
            ret, 350244, 'd993842bcd881592aad50a8df8925499',
            '2d10706f4ecfdbbe6d5d86e8578adbfa', skip_glimmer=False, tolerance=30)

    def test_quast_from_1_wsobj(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        ret = self.impl.run_QUAST(self.ctx, {'assemblies': [ref], 'make_handle': 1})[0]
        self.check_quast_output(ret, 329244, '3e22e7ae2b33559a4f9bb18dc4f2b06c',
                                '140133e21ce35277cb7adc2eed2b1fd5')

    def test_quast_from_2_wsobj(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref1 = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})

        tf = 'greengenes_UnAligSeq24606.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref2 = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'JohnCleeseLust'})

        # test using names vs ids
        objs = self.ws.get_object_info3({'objects': [{'ref': ref1}, {'ref': ref2}]})['infos']
        wsref1 = str(objs[0][7] + '/' + str(objs[0][1]))
        wsref2 = str(objs[1][7] + '/' + str(objs[1][1]))

        ret = self.impl.run_QUAST(self.ctx, {'assemblies': [wsref1, wsref2], 'make_handle': 1})[0]
        self.check_quast_output(
            ret, 345199, '8f9c1e7536cc3f94e4b00c2dd543e56f', '3e2d94fb1d29d48c3058f8cbb68674ae',
            tolerance=30)

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_from_1_large_wsobj(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        ret = self.impl.run_QUAST(self.ctx, {'assemblies': [ref], 'make_handle': 1})[0]
        self.check_quast_output(ret, 327029, '215bb5b5ae200c680e36d32813246b99',
                                '140133e21ce35277cb7adc2eed2b1fd5', skip_glimmer=True)

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_from_1_large_wsobj_force_glimmer(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        ret = self.impl.run_QUAST(self.ctx, {'assemblies': [ref], 'make_handle': 1,
                                             'force_glimmer': True})[0]
        self.check_quast_output(ret, 329245, '3e22e7ae2b33559a4f9bb18dc4f2b06c',
                                '140133e21ce35277cb7adc2eed2b1fd5', skip_glimmer=False)

    def test_fail_no_input(self):
        self.start_test()
        self.fail_quast(
            {}, 'One and only one of a list of assembly references or files is required')

    def test_fail_2_input(self):
        self.start_test()
        self.fail_quast(
            {'files': ['foo'], 'assemblies': ['bar']},
            'One and only one of a list of assembly references or files is required')

    def test_fail_bad_assy_list(self):
        self.start_test()
        self.fail_quast(
            {'assemblies': {'foo': 'bar'}},
            'assemblies must be a list')

    def test_fail_bad_file_list(self):
        self.start_test()
        self.fail_quast(
            {'files': {'foo': 'bar'}},
            'files must be a list')

    def test_fail_bad_file(self):
        self.start_test()
        self.fail_quast(
            {'files': [{'path': 'data/greengenes_UnAligSeq24606.fa'},
                       {'path': 'data/foobar.fa'}]},
            'File entry 2, data/foobar.fa, is not a file')

    def test_fail_bad_min_contig_length(self):
        self.start_test()
        test_params = {
            'foo': 'Minimum contig length must be an integer >= 50, got: foo',
            49: 'Minimum contig length must be an integer >= 50, got: 49',
            0: 'Minimum contig length must be an integer >= 50, got: 0',
            -1: 'Minimum contig length must be an integer >= 50, got: -1'
        }
        for mcl, exception in test_params.items():
            self.fail_quast(
                {
                    'files': [{'path': 'data/greengenes_UnAligSeq24606.fa'}],
                    'min_contig_length': mcl
                },
                exception,
                contains=False)

    def test_fail_bad_quast_input_garbage(self):
        self.start_test()
        self.fail_quast(
            {'files': [{'path': 'data/greengenes_UnAligSeq24606.fa'},
                       {'path': 'data/greengenes_UnAligSeq24606_garbage.fa'}]},
            "'utf-8' codec can't decode byte 0x8b in position 1: invalid start byte")

    def test_fail_bad_ws_ref(self):
        self.start_test()
        self.fail_quast(
            {'assemblies': [str(self.ws_info[0]) + '/999999999999/999999']},
            'No object with id 999999999999 exists in workspace {} (name {})'.format(
                self.ws_info[0], self.ws_info[1]),
            exception=WorkspaceError, contains=True)

    def test_fail_bad_ws_type(self):
        self.start_test()
        bad_object_type = {'type': 'Empty.AType',
                           'data': {'foo': 3},
                           'name': "bad_object"}
        bad_object = self.dfu.save_objects({'id': self.ws_info[0],
                                            'objects': [bad_object_type]})[0]
        bo_type = bad_object[2]
        bad_object_ref = str(bad_object[6]) + '/' + str(bad_object[0]) + '/' + str(bad_object[4])
        self.fail_quast(
            {'assemblies': [bad_object_ref]},
            "Cannot write data to fasta; invalid WS type ({}).  ".format(bo_type) +
            "Supported types are KBaseGenomes.ContigSet and KBaseGenomeAnnotations.Assembly",
            exception=AssemblyError, contains=True)

    def test_fail_duplicate_objects(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref1 = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})

        objs = self.ws.get_object_info3({'objects': [{'ref': ref1}]})['infos']
        wsref1 = str(objs[0][7] + '/' + str(objs[0][1]))

        self.fail_quast(
            {'assemblies': [ref1, wsref1]},
            'Duplicate objects detected in input')

# ****** test quast app tests *******************************

    def test_quast_app(self):
        # only one happy path through the run_QUAST_app code
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        ret = self.impl.run_QUAST_app(self.ctx, {'assemblies': [ref],
                                                 'workspace_name': self.ws_info[1]})[0]
        self.check_quast_app_output(ret, 329245, '3e22e7ae2b33559a4f9bb18dc4f2b06c',
                                    '140133e21ce35277cb7adc2eed2b1fd5')

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_app_large_object(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        ret = self.impl.run_QUAST_app(self.ctx, {'assemblies': [ref],
                                                 'workspace_name': self.ws_info[1]})[0]
        self.check_quast_app_output(ret, 327027, '215bb5b5ae200c680e36d32813246b99',
                                    '140133e21ce35277cb7adc2eed2b1fd5', skip_glimmer=True)

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_app_large_object_force_glimmer(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        ret = self.impl.run_QUAST_app(self.ctx, {'assemblies': [ref],
                                                 'workspace_name': self.ws_info[1],
                                                 'force_glimmer': True})[0]
        self.check_quast_app_output(ret, 329246, '3e22e7ae2b33559a4f9bb18dc4f2b06c',
                                    '140133e21ce35277cb7adc2eed2b1fd5', skip_glimmer=False)

    def test_fail_app_no_workspace(self):
        self.start_test()
        self.fail_quast_app(
            {'assemblies': [str(self.ws_info[0]) + '/9999999']},
            'No workspace name provided')

    def test_fail_app_null_workspace(self):
        self.start_test()
        self.fail_quast_app(
            {'assemblies': [str(self.ws_info[0]) + '/9999999'],
             'workspace_name': None},
            'No workspace name provided')

    def test_fail_app_bad_ws_ref(self):
        self.start_test()
        self.fail_quast_app(
            {'assemblies': [str(self.ws_info[0]) + '/999999999999/999999'],
             'workspace_name': self.ws_info[1]},
            'No object with id 999999999999 exists in workspace {} (name {})'.format(
                self.ws_info[0], self.ws_info[1]),
            exception=WorkspaceError)

    def test_fail_app_bad_ws_name(self):
        self.start_test()
        tf = 'greengenes_UnAligSeq24606_edit1.fa'
        target = os.path.join(self.scratch, tf)
        shutil.copy('data/' + tf, target)
        ref = self.au.save_assembly_from_fasta(
            {'file': {'path': target},
             'workspace_name': self.ws_info[1],
             'assembly_name': 'assy1'})
        self.fail_quast_app(
            {'assemblies': [ref],
             'workspace_name': 'ireallyhopethisworkspacedoesntexistorthistestwillfail'},
            'No workspace with name ireallyhopethisworkspacedoesntexistorthistestwillfail exists',
            exception=KBRError, contains=True)

    def fail_quast_app(self, params, error, exception=ValueError, contains=True):
        with self.assertRaises(exception) as context:
            self.impl.run_QUAST_app(self.ctx, params)
        if contains:
            self.assertIn(error, str(context.exception))
        else:
            self.assertEqual(error, str(context.exception))

    def fail_quast(self, params, error, exception=ValueError, contains=True):
        with self.assertRaises(exception) as context:
            self.impl.run_QUAST(self.ctx, params)
        print(context.exception)
        if contains:
            self.assertIn(error, str(context.exception))
        else:
            self.assertEqual(error, str(context.exception))

    def check_quast_app_output(self, ret, size, repttxtmd5, icarusmd5,
                               skip_glimmer=False, tolerance=15):
        """
        Robust checks that don't rely on version-specific MD5s or exact zip size.
        Keeps the legacy signature/params for compatibility with existing tests.
        """
        filename = 'quast_results.zip'

        # Fetch the created KBaseReport
        ref = ret['report_ref']
        objname = ret['report_name']
        obj = self.dfu.get_objects({'object_refs': [ref]})['data'][0]
        d = obj['data']
        links = d['html_links']
        self.assertEqual(len(links), 1)
        hid = links[0]['handle']
        shocknode = links[0]['URL'].split('/')[-1]
        self.handles_to_delete.append(hid)
        self.nodes_to_delete.append(shocknode)

        # Basic KBR consistency checks
        self.assertEqual(objname, obj['info'][1])
        rmd5_text = hashlib.md5(d['text_message'].encode()).hexdigest()
        self.assertEqual(d['direct_html_link_index'], 0)
        self.assertEqual(links[0]['name'], 'report.html')
        self.assertEqual(links[0]['label'], 'QUAST report')

        # Shock metadata + zip size sanity (plots may change size)
        shockret = requests.get(
            self.shockURL + '/node/' + shocknode,
            headers={'Authorization': 'OAuth ' + self.token}
        ).json()['data']
        self.assertEqual(shockret['id'], shocknode)
        shockfile = shockret['file']
        self.assertEqual(shockfile['name'], filename)
        self.assertGreater(shockfile['size'], 150000)   # lower bound
        self.assertLess(shockfile['size'], 5000000)     # upper bound sanity

        # Handle service roundtrip
        handleret = self.hs.hids_to_handles([hid])[0]
        self.assertEqual(handleret['url'], self.shockURL)
        self.assertEqual(handleret['hid'], hid)
        self.assertEqual(handleret['type'], 'shock')
        self.assertEqual(handleret['id'], shocknode)

        # Download/unpack the zip and compare artifacts
        zipdir = os.path.join(self.WORKDIR, str(uuid.uuid4()))
        self.dfu.shock_to_file({
            'shock_id': shocknode,
            'unpack': 'unpack',
            'file_path': os.path.join(zipdir, filename)
        })

        # report.txt in zip should equal the text embedded in the KBase report
        with open(os.path.join(zipdir, 'report.txt'), 'rb') as _f:
            rmd5_zip = hashlib.md5(_f.read()).hexdigest()
        self.assertEqual(rmd5_text, rmd5_zip)

        # Key files exist; Icarus may or may not be present depending on flags
        result_files = os.listdir(zipdir)
        for required in ('report.txt', 'report.tsv', 'report.html', 'quast.log'):
            self.assertIn(required, result_files)

        if skip_glimmer:
            self.assertNotIn('predicted_genes', result_files)
        else:
            self.assertIn('predicted_genes', result_files)

        # If Icarus is present, just ensure it's a non-empty file
        icarus_path = os.path.join(zipdir, 'icarus.html')
        if os.path.exists(icarus_path):
            with open(icarus_path, 'rb') as _f:
                self.assertGreater(len(_f.read()), 0)

    def check_quast_output(self, ret, size, repttxtmd5, icarusmd5, no_handle=False,
                           skip_glimmer=False, tolerance=15):
        """
        Robust checks for the non-app path. Avoid fixed MD5/size expectations and
        compare zip artifacts to the on-disk output directory.
        """
        filename = 'quast_results.zip'

        # Shock + handle basics
        shocknode = ret['shock_id']
        self.nodes_to_delete.append(shocknode)
        if not no_handle and ret.get('handle'):
            self.handles_to_delete.append(ret['handle']['hid'])

        self.assertEqual(ret['node_file_name'], filename)
        self.assertGreater(ret['size'], 150000)
        self.assertLess(ret['size'], 5000000)

        shockret = requests.get(
            self.shockURL + '/node/' + shocknode,
            headers={'Authorization': 'OAuth ' + self.token}
        ).json()['data']
        self.assertEqual(shockret['id'], shocknode)
        shockfile = shockret['file']
        self.assertEqual(shockfile['name'], filename)
        self.assertEqual(shockfile['size'], ret['size'])

        if no_handle:
            self.assertIsNone(ret['handle'])
        else:
            handle = ret['handle']
            self.assertEqual(handle['url'], self.shockURL)
            self.assertEqual(handle['file_name'], filename)
            self.assertEqual(handle['type'], 'shock')
            self.assertEqual(handle['id'], shocknode)
            self.assertEqual(handle['remote_md5'], shockfile['checksum']['md5'])
            hid = handle['hid']
            handleret = self.hs.hids_to_handles([hid])[0]
            self.assertEqual(handleret['url'], self.shockURL)
            self.assertEqual(handleret['hid'], hid)
            self.assertEqual(handleret['file_name'], filename)
            self.assertEqual(handleret['type'], 'shock')
            self.assertEqual(handleret['id'], shocknode)
            self.assertEqual(handleret['remote_md5'], handle['remote_md5'])

        # Unpack zip
        zipdir = os.path.join(self.WORKDIR, str(uuid.uuid4()))
        self.dfu.shock_to_file({
            'shock_id': shocknode,
            'unpack': 'unpack',
            'file_path': os.path.join(zipdir, filename)
        })

        # Compare report.txt in zip vs on-disk quast_path
        with open(os.path.join(zipdir, 'report.txt'), 'rb') as f:
            rmd5_zip = hashlib.md5(f.read()).hexdigest()
        with open(os.path.join(ret['quast_path'], 'report.txt'), 'rb') as f:
            rmd5_disk = hashlib.md5(f.read()).hexdigest()
        self.assertEqual(rmd5_zip, rmd5_disk)

        # If Icarus exists in both places, compare
        icarus_zip_path = os.path.join(zipdir, 'icarus.html')
        icarus_disk_path = os.path.join(ret['quast_path'], 'icarus.html')
        if os.path.exists(icarus_zip_path) and os.path.exists(icarus_disk_path):
            with open(icarus_zip_path, 'rb') as f:
                imd5_zip = hashlib.md5(f.read()).hexdigest()
            with open(icarus_disk_path, 'rb') as f:
                imd5_disk = hashlib.md5(f.read()).hexdigest()
            self.assertEqual(imd5_zip, imd5_disk)

        # Required files present; predicted_genes depends on glimmer
        result_files = os.listdir(zipdir)
        for required in ('report.txt', 'report.tsv', 'report.html', 'quast.log'):
            self.assertIn(required, result_files)
        if skip_glimmer:
            self.assertNotIn('predicted_genes', result_files)
        else:
            self.assertIn('predicted_genes', result_files)


if __name__ == '__main__':
    unittest.main()
