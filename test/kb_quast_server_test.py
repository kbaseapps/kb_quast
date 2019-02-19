# -*- coding: utf-8 -*-
import hashlib
import inspect
import os  # noqa: F401
import shutil
import time
import unittest
import uuid
from configparser import ConfigParser  # py3 @UnresolvedImport @Reimport
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
from kb_quast.authclient import KBaseAuth as _KBaseAuth
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
        authServiceUrl = cls.cfg.get('auth-service-url',
                "https://kbase.us/services/authorization/Sessions/Login")
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(cls.token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_quast',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.shockURL = cls.cfg['shock-url']
        cls.ws = Workspace(cls.cfg['workspace-url'], token=cls.token)
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
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
#         cls.setupTestData()
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
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
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
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}],
            'make_handle': 1})[0]
        self.check_quast_output(ret, 329105, 'a8ee2a3d96a3857105987c960185f307',
                                '6522bf4c7a54f96b99f7097c1a6afb01')

    def test_quast_no_handle(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}],
            'make_handle': 0})[0]
        self.check_quast_output(ret, 329100, 'a8ee2a3d96a3857105987c960185f307',
                                '6522bf4c7a54f96b99f7097c1a6afb01', no_handle=True)

        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}]})[0]
        self.check_quast_output(ret, 329100, 'a8ee2a3d96a3857105987c960185f307',
                                '6522bf4c7a54f96b99f7097c1a6afb01', no_handle=True)

    def test_quast_from_2_files(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
            {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}],
            'make_handle': 1})[0]
        self.check_quast_output(ret, 349155, '365aa50eda257a514b7fbae4edfba0a7',
                                '2d10706f4ecfdbbe6d5d86e8578adbfa')

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_large_file(self):
        self.start_test()

        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
            {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}],
            'make_handle': 1})[0]

        self.check_quast_output(ret, 345220, 'e8c7d24f35a8c3feb1da4c58623ad277',
                                '2d10706f4ecfdbbe6d5d86e8578adbfa', skip_glimmer=True)

    @patch.object(kb_quast, "TWENTY_MB", new=10)
    def test_quast_large_file_force_glimmer(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
            {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}],
            'make_handle': 1,
            'force_glimmer': True})[0]
        self.check_quast_output(ret, 349150, '365aa50eda257a514b7fbae4edfba0a7',
                                '2d10706f4ecfdbbe6d5d86e8578adbfa', skip_glimmer=False)

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
        self.check_quast_output(ret, 328570, 'f8a8b01c9939614b50381d9a760c3ee4',
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
        self.check_quast_output(ret, 344240, 'a44837b572fd48e6cd4179399b9aacd7',
                                '3e2d94fb1d29d48c3058f8cbb68674ae')

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
        self.check_quast_output(ret, 326336, '26876f8e773af163cf0e2518bbd28ab7',
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
        self.check_quast_output(ret, 328567, 'f8a8b01c9939614b50381d9a760c3ee4',
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
            {'files': [{'path': 'data/greengenes_UnAligSeq24606.fa'}, {'path': 'data/foobar.fa'}]},
            'File entry 2, data/foobar.fa, is not a file')

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
                           'name': "bad_object"
                           }
        bad_object = self.dfu.save_objects({'id': self.ws_info[0],
                                            'objects':
                                            [bad_object_type]})[0]
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
        self.check_quast_app_output(ret, 328570, 'f8a8b01c9939614b50381d9a760c3ee4',
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
        self.check_quast_app_output(ret, 326340, '26876f8e773af163cf0e2518bbd28ab7',
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
        self.check_quast_app_output(ret, 328560, 'f8a8b01c9939614b50381d9a760c3ee4',
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
        minsize = size - tolerance
        maxsize = size + tolerance
        filename = 'quast_results.zip'

        ref = ret['report_ref']
        objname = ret['report_name']
        obj = self.dfu.get_objects(
            {'object_refs': [ref]})['data'][0]
        print(obj)
        d = obj['data']
        links = d['html_links']
        self.assertEqual(len(links), 1)
        hid = links[0]['handle']
        shocknode = links[0]['URL'].split('/')[-1]
        self.handles_to_delete.append(hid)
        self.nodes_to_delete.append(shocknode)

        self.assertEqual(objname, obj['info'][1])
        rmd5 = hashlib.md5(d['text_message'].encode()).hexdigest()
        self.assertEqual(d['direct_html_link_index'], 0)
        self.assertEqual(rmd5, repttxtmd5)
        self.assertEqual(links[0]['name'], 'report.html')
        self.assertEqual(links[0]['label'], 'QUAST report')

        shockret = requests.get(self.shockURL + '/node/' + shocknode,
                                headers={'Authorization': 'OAuth ' + self.token}).json()['data']
        self.assertEqual(shockret['id'], shocknode)
        shockfile = shockret['file']
        self.assertEqual(shockfile['name'], filename)
        self.assertGreater(shockfile['size'], minsize)  # zip file size & md5 not repeatable
        self.assertLess(shockfile['size'], maxsize)

        handleret = self.hs.hids_to_handles([hid])[0]
        print(handleret)
        self.assertEqual(handleret['url'], self.shockURL)
        self.assertEqual(handleret['hid'], hid)
#         self.assertEqual(handleret['file_name'], filename)  # KBR doesn't set
        self.assertEqual(handleret['type'], 'shock')
        self.assertEqual(handleret['id'], shocknode)
        # KBR doesn't set
#         self.assertEqual(handleret['remote_md5'], shockfile['checksum']['md5'])

        # check data in shock
        zipdir = os.path.join(self.WORKDIR, str(uuid.uuid4()))
        self.dfu.shock_to_file(
            {'shock_id': shocknode,
             'unpack': 'unpack',
             'file_path': os.path.join(zipdir, filename)
             })
        rmd5 = hashlib.md5(open(os.path.join(zipdir, 'report.txt'), 'rb')
                           .read()).hexdigest()
        self.assertEqual(rmd5, repttxtmd5)
        imd5 = hashlib.md5(open(os.path.join(zipdir, 'icarus.html'), 'rb')
                           .read()).hexdigest()
        self.assertEqual(imd5, icarusmd5)

        result_files = os.listdir(zipdir)
        if skip_glimmer:
            self.assertNotIn('predicted_genes', result_files)
        else:
            self.assertIn('predicted_genes', result_files)

    def check_quast_output(self, ret, size, repttxtmd5, icarusmd5, no_handle=False,
                           skip_glimmer=False, tolerance=15):
        minsize = size - tolerance
        maxsize = size + tolerance
        filename = 'quast_results.zip'

        shocknode = ret['shock_id']
        self.nodes_to_delete.append(shocknode)
        if not no_handle:
            self.handles_to_delete.append(ret['handle']['hid'])
        self.assertEqual(ret['node_file_name'], filename)
        self.assertGreater(ret['size'], minsize)  # zip file size & md5 not repeatable
        self.assertLess(ret['size'], maxsize)
        shockret = requests.get(self.shockURL + '/node/' + shocknode,
                                headers={'Authorization': 'OAuth ' + self.token}).json()['data']
        self.assertEqual(shockret['id'], shocknode)
        shockfile = shockret['file']
        self.assertEqual(shockfile['name'], filename)
        self.assertEqual(shockfile['size'], ret['size'])
        if no_handle:
            self.assertEqual(ret['handle'], None)
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

        # check data in shock
        zipdir = os.path.join(self.WORKDIR, str(uuid.uuid4()))
        self.dfu.shock_to_file(
            {'shock_id': shocknode,
             'unpack': 'unpack',
             'file_path': os.path.join(zipdir, filename)
             })
        rmd5 = hashlib.md5(open(os.path.join(zipdir, 'report.txt'), 'rb')
                           .read()).hexdigest()
        self.assertEqual(rmd5, repttxtmd5)
        imd5 = hashlib.md5(open(os.path.join(zipdir, 'icarus.html'), 'rb')
                           .read()).hexdigest()
        self.assertEqual(imd5, icarusmd5)

        # check data on disk
        rmd5 = hashlib.md5(open(os.path.join(ret['quast_path'], 'report.txt'), 'rb')
                           .read()).hexdigest()
        self.assertEqual(rmd5, repttxtmd5)
        imd5 = hashlib.md5(open(os.path.join(ret['quast_path'], 'icarus.html'), 'rb')
                           .read()).hexdigest()
        self.assertEqual(imd5, icarusmd5)

        # check predicted_genes directory exitance 
        result_files = os.listdir(zipdir)
        if skip_glimmer:
            self.assertNotIn('predicted_genes', result_files)
        else:
            self.assertIn('predicted_genes', result_files)
