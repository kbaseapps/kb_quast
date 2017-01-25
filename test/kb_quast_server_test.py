# -*- coding: utf-8 -*-
import unittest
import os  # noqa: F401
import time
import requests

from os import environ
import shutil
import uuid
import hashlib
import inspect
try:
    from ConfigParser import ConfigParser  # py2 @UnusedImport
except:
    from configparser import ConfigParser  # py3 @UnresolvedImport @Reimport

from Workspace.WorkspaceClient import Workspace
from Workspace.baseclient import ServerError as WorkspaceError
from AbstractHandle.AbstractHandleClient import AbstractHandle as HandleService
from DataFileUtil.DataFileUtilClient import DataFileUtil
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
from AssemblyUtil.baseclient import ServerError as AssemblyError
from KBaseReport.baseclient import ServerError as KBRError
from kb_quast.kb_quastImpl import kb_quast
from kb_quast.kb_quastServer import MethodContext


class kb_quastTest(unittest.TestCase):

    WORKDIR = '/kb/module/work/tmp/'

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        user_id = requests.post(
            'https://kbase.us/services/authorization/Sessions/Login',
            data='token={}&fields=user_id'.format(cls.token)).json()['user_id']
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
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_quast'):
            cls.cfg[nameval[0]] = nameval[1]
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

    def test_quast_from_1_file(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}],
                                             'make_handle': 1})[0]
        self.check_quast_output(ret, 315250, 315280, '51b78e4ff2ff7a2f864769ff02d95f92',
                                'dff937c5ed36a38345d057ea0b5c3e9e')

    def test_quast_no_handle(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}],
                                             'make_handle': 0})[0]
        self.check_quast_output(ret, 315250, 315280, '51b78e4ff2ff7a2f864769ff02d95f92',
                                'dff937c5ed36a38345d057ea0b5c3e9e', no_handle=True)

        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}]})[0]
        self.check_quast_output(ret, 315250, 315280, '51b78e4ff2ff7a2f864769ff02d95f92',
                                'dff937c5ed36a38345d057ea0b5c3e9e', no_handle=True)

    def test_quast_from_2_files(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
            {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}],
                                             'make_handle': 1})[0]
        self.check_quast_output(ret, 324690, 324740, 'b45307b9bed53de2fa0d0b9780be3faf',
                                '862913a9383b42d0f0fb95beb113296f')

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
        self.check_quast_output(ret, 315180, 315200, '6aae4f232d4d011210eca1965093c22d',
                                '2010dc270160ee661d76dad6051cda32')

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
        self.check_quast_output(ret, 320910, 320950, '5648903ef181d4ab189a206f6be28c47',
                                'f48d2c38619ef93ae8972ce4e6ebcbf4')

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
            'QUAST skipped some files - 2 expected, 1 processed.')

    def test_fail_bad_ws_ref(self):
        self.start_test()
        self.fail_quast(
            {'assemblies': [str(self.ws_info[0]) + '/999999999999/999999']},
            'No object with id 999999999999 exists in workspace {} (name {})'.format(
                self.ws_info[0], self.ws_info[1]),
            exception=WorkspaceError)

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
        md5type = self.ws.translate_to_MD5_types([bo_type])[bo_type]
        bad_object_ref = str(bad_object[6]) + '/' + str(bad_object[0]) + '/' + str(bad_object[4])
        self.fail_quast(
            {'assemblies': [bad_object_ref]},
            "Invalid type! Expected one of ['KBaseGenomes.ContigSet', " +
            "'KBaseGenomeAnnotations.Assembly'], received {}".format(md5type),
            exception=AssemblyError)

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
        self.check_quast_app_output(ret, 315170, 315200, '6aae4f232d4d011210eca1965093c22d',
                                    '2010dc270160ee661d76dad6051cda32')

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
            self.assertIn(error, str(context.exception.message))
        else:
            self.assertEqual(error, str(context.exception.message))

    def fail_quast(self, params, error, exception=ValueError):
        with self.assertRaises(exception) as context:
            self.impl.run_QUAST(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def check_quast_app_output(self, ret, minsize, maxsize, repttxtmd5, icarusmd5):
        filename = 'quast_results.zip'

        ref = ret['report_ref']
        objname = ret['report_name']
        obj = self.dfu.get_objects(
            {'object_refs': [ref]})['data'][0]
        print obj
        d = obj['data']
        links = d['html_links']
        self.assertEqual(len(links), 1)
        hid = links[0]['handle']
        shocknode = links[0]['URL'].split('/')[-1]
        self.handles_to_delete.append(hid)
        self.nodes_to_delete.append(shocknode)

        self.assertEqual(objname, obj['info'][1])
        rmd5 = hashlib.md5(d['text_message']).hexdigest()
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
        print handleret
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
        self.assertEquals(rmd5, repttxtmd5)
        imd5 = hashlib.md5(open(os.path.join(zipdir, 'icarus.html'), 'rb')
                           .read()).hexdigest()
        self.assertEquals(imd5, icarusmd5)

    def check_quast_output(self, ret, minsize, maxsize, repttxtmd5, icarusmd5, no_handle=False):
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
        self.assertEquals(rmd5, repttxtmd5)
        imd5 = hashlib.md5(open(os.path.join(zipdir, 'icarus.html'), 'rb')
                           .read()).hexdigest()
        self.assertEquals(imd5, icarusmd5)

        # check data on disk
        rmd5 = hashlib.md5(open(os.path.join(ret['quast_path'], 'report.txt'), 'rb')
                           .read()).hexdigest()
        self.assertEquals(rmd5, repttxtmd5)
        imd5 = hashlib.md5(open(os.path.join(ret['quast_path'], 'icarus.html'), 'rb')
                           .read()).hexdigest()
        self.assertEquals(imd5, icarusmd5)
