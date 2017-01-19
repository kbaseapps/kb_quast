# -*- coding: utf-8 -*-
#BEGIN_HEADER
import errno as _errno
import os as _os
import time as _time
import uuid as _uuid
import subprocess as _subprocess
from Workspace.WorkspaceClient import Workspace as _WSClient
from Workspace.baseclient import ServerError as _WSError
from DataFileUtil.DataFileUtilClient import DataFileUtil as _DFUClient
from DataFileUtil.baseclient import ServerError as _DFUError
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil as _AssClient
from AssemblyUtil.baseclient import ServerError as _AssError
from KBaseReport.KBaseReportClient import KBaseReport as _KBRepClient
import psutil


class ObjInfo(object):

    def __init__(self, obj_info):
        self.id = obj_info[0]
        self.name = obj_info[1]
        self.type, self.type_ver = obj_info[2].split('-')
        self.time = obj_info[3]
        self.version = obj_info[4]
        self.saved_by = obj_info[5]
        self.wsid = obj_info[6]
        self.workspace = obj_info[7]
        self.chsum = obj_info[8]
        self.size = obj_info[9]
        self.meta = obj_info[10]
        self.ref = str(self.wsid) + str(self.id) + str(self.version)
#END_HEADER


class kb_quast:
    '''
    Module Name:
    kb_quast

    Module Description:
    Wrapper for the QUAST tool. Takes one or more assemblies as input and produces a QUAST report
stored in a zip file in Shock.
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/mrcreosote/kb_quast"
    GIT_COMMIT_HASH = "449f6a5c981fc8958ca68017bf206321e9f39ac2"

    #BEGIN_CLASS_HEADER

    ALLOWED_TYPES = ['KBaseGenomes.ContigSet', 'KBaseGenomeAnnotations.Assembly']

    THREADS_PER_CORE = 1

    def log(self, message, prefix_newline=False):
        print(('\n' if prefix_newline else '') + str(_time.time()) + ': ' + message)

    def xor(self, a, b):
        return bool(a) != bool(b)

    # http://stackoverflow.com/a/600612/643675
    def mkdir_p(self, path):
        if not path:
            return
        try:
            _os.makedirs(path)
        except OSError as exc:
            if exc.errno == _errno.EEXIST and _os.path.isdir(path):
                pass
            else:
                raise

    def get_assemblies(self, target_dir, object_infos):
        filepaths = []
        asscli = _AssClient(self.callback_url)
        # would be nice the the assembly utils had bulk download...
        for i in object_infos:
            fn = _os.path.join(target_dir, i.ref.replace('/', '_'))
            filepaths.append(fn)
            self.log('getting assembly from object {} and storing at {}'.format(i.ref, fn))
            try:
                asscli.get_assembly_as_fasta({'ref': i.ref, 'filename': fn})
            except _AssError as asserr:
                self.log('Logging assembly downloader exception')
                self.log(str(asserr))
                raise
        return filepaths

    def get_assembly_object_info(self, assemblies, token):
        refs = [{'ref': x} for x in assemblies]
        ws = _WSClient(self.ws_url, token=token)
        self.log('Getting object information from workspace')
        # TODO use this often enough that should add to DFU but return dict vs list
        try:
            info = [ObjInfo(i) for i in ws.get_object_info3({'objects': refs})['infos']]
        except _WSError as wse:
            self.log('Logging workspace exception')
            self.log(str(wse))
            raise
        self.log('Object list:')
        for i in info:
            self.log('{}/{} {} {}'.format(i.workspace, i.name, i.ref, i.type))
            if i.type not in self.ALLOWED_TYPES:
                raise ValueError('Object {} ({}/{}) type {} is not an assembly'
                                 .format(i.ref, i.workspace, i.name, i.type))
        absrefs = [i.ref for i in info]
        if len(set(absrefs)) != len(absrefs):
            raise ValueError('Duplicate objects detected in input')  # could list objs later

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.scratch = config['scratch']
        self.callback_url = _os.environ['SDK_CALLBACK_URL']
        self.ws_url = config['workspace-url']
        #END_CONSTRUCTOR
        pass

    def run_QUAST_app(self, ctx, params):
        """
        Run QUAST and save a KBaseReport with the output.
        :param params: instance of type "QUASTParams" (Input for running
           QUAST. assemblies - the list of assemblies upon which QUAST will
           be run. -OR- files - the list of FASTA files upon which QUAST will
           be run.) -> structure: parameter "assemblies" of list of type
           "assembly_ref" (An X/Y/Z style reference to a workspace object
           containing an assembly, either a KBaseGenomes.ContigSet or
           KBaseGenomeAnnotations.Assembly.), parameter "files" of list of
           type "FASTAFile" (A local FASTA file. path - the path to the FASTA
           file. label - the label to use for the file in the QUAST output.
           If missing, the file name will be used.) -> structure: parameter
           "path" of String, parameter "label" of String
        :returns: instance of type "QUASTAppOutput" (Output of the
           run_quast_app function. report_name - the name of the
           KBaseReport.Report workspace object. report_ref - the workspace
           reference of the report.) -> structure: parameter "report_name" of
           String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_QUAST_app
        output = None
        #END run_QUAST_app

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_QUAST_app return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def run_QUAST(self, ctx, params):
        """
        Run QUAST and return a shock node containing the zipped QUAST output.
        :param params: instance of type "QUASTParams" (Input for running
           QUAST. assemblies - the list of assemblies upon which QUAST will
           be run. -OR- files - the list of FASTA files upon which QUAST will
           be run.) -> structure: parameter "assemblies" of list of type
           "assembly_ref" (An X/Y/Z style reference to a workspace object
           containing an assembly, either a KBaseGenomes.ContigSet or
           KBaseGenomeAnnotations.Assembly.), parameter "files" of list of
           type "FASTAFile" (A local FASTA file. path - the path to the FASTA
           file. label - the label to use for the file in the QUAST output.
           If missing, the file name will be used.) -> structure: parameter
           "path" of String, parameter "label" of String
        :returns: instance of type "QUASTOutput" (Ouput of the run_quast
           function. shock_id - the id of the shock node where the zipped
           QUAST output is stored. handle - the new handle for the shock
           node. node_file_name - the name of the file stored in Shock. size
           - the size of the file stored in shock. quast_path - the directory
           containing the quast output and the zipfile of the directory.) ->
           structure: parameter "shock_id" of String, parameter "handle" of
           type "Handle" (A handle for a file stored in Shock. hid - the id
           of the handle in the Handle Service that references this shock
           node id - the id for the shock node url - the url of the shock
           server type - the type of the handle. This should always be shock.
           file_name - the name of the file remote_md5 - the md5 digest of
           the file.) -> structure: parameter "hid" of String, parameter
           "file_name" of String, parameter "id" of String, parameter "url"
           of String, parameter "type" of String, parameter "remote_md5" of
           String, parameter "node_file_name" of String, parameter "size" of
           String, parameter "quast_path" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_QUAST
        self.log('Starting QUAST run. Parameters:')
        self.log(str(params))
        assemblies = params.get('assemblies')
        files = params.get('files')
        if not self.xor(assemblies, files):
            raise ValueError(
                'One and only one of a list of assembly references or files is required')
        tdir = _os.path.join(self.scratch, str(_uuid.uuid4()))
        self.mkdir_p(tdir)
        if assemblies:
            if type(assemblies) != list:
                raise ValueError('assemblies must be a list')
            self.log('Getting object information from workspace')
            info = self.get_assembly_object_info(assemblies, ctx['token'])
            filepaths = self.get_assemblies(tdir, info)
            labels = [i.name for i in info]
        else:
            if type(files) != list:
                raise ValueError('files must be a list')
            filepaths = []
            labels = []
            for i, lp in enumerate(files):
                l = lp.get('label')
                p = lp.get('path')
                if not _os.path.isfile(p):
                    raise ValueError('File entry {}, {}, is not a file'.format(i + 1, p))
                l = l if l else _os.path.basename(p)
                filepaths.append(p)
                labels.append(l)

        out = _os.path.join(tdir, 'quast_results')
        # TODO check for name duplicates in labels and do something about it
        threads = psutil.cpu_count() * self.THREADS_PER_CORE
        # DO NOT use genemark instead of glimmer, not open source
        # DO NOT use metaQUAST, uses SILVA DB which is not open source
        cmd = ['quast.py', '--threads', str(threads), '-o', out, '--labels', ','.join(labels),
               '--glimmer', '--contig-thresholds', '0,1000,10000,100000,1000000'] + filepaths
        self.log('running QUAST with command line ' + str(cmd))
        retcode = _subprocess.call(cmd)
        self.log('QUAST return code: ' + str(retcode))
        if retcode:
            raise ValueError('QUAST reported an error, return code was ' + str(retcode))
        dfu = _DFUClient(self.callback_url)
        try:
            output = dfu.file_to_shock({'file_path': out, 'make_handle': 1, 'pack': 'zip'})
        except _DFUError as dfue:
            self.log('Logging exception loading results to shock')
            self.log(str(dfue))
            raise
        output['quast_path'] = out
        #END run_QUAST

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_QUAST return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def status(self, ctx):
        #BEGIN_STATUS
        del ctx
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
