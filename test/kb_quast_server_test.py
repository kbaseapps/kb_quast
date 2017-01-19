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
from AbstractHandle.AbstractHandleClient import AbstractHandle as HandleService
from DataFileUtil.DataFileUtilClient import DataFileUtil
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
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
        test_name = inspect.stack()[1][3]
        print('\n*** starting test: ' + test_name + ' **')

    def test_quast_from_1_file(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foobar'}]})[0]
        self.check_quast_output(ret, 315250, 315280, '51b78e4ff2ff7a2f864769ff02d95f92',
                                'dff937c5ed36a38345d057ea0b5c3e9e')

    def test_quast_from_2_files(self):
        self.start_test()
        ret = self.impl.run_QUAST(self.ctx, {'files': [
            {'path': 'data/greengenes_UnAligSeq24606.fa', 'label': 'foo'},
            {'path': 'data/greengenes_UnAligSeq24606_edit1.fa'}]})[0]
        self.check_quast_output(ret, 324700, 324730, 'b45307b9bed53de2fa0d0b9780be3faf',
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
        print ref
        ret = self.impl.run_QUAST(self.ctx, {'assemblies': [ref]})[0]
        self.check_quast_output(ret, 315180, 315200, '6aae4f232d4d011210eca1965093c22d',
                                '2010dc270160ee661d76dad6051cda32')

    def check_quast_output(self, ret, minsize, maxsize, repttxtmd5, icarusmd5):
        filename = 'quast_results.zip'

        shocknode = ret['shock_id']
        self.nodes_to_delete.append(shocknode)
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
