# -*- coding: utf-8 -*-
#BEGIN_HEADER
import errno as _errno
import os as _os
import subprocess as _subprocess
import time as _time
import uuid as _uuid

import psutil
from Bio import SeqIO as _SeqIO

from installed_clients.AssemblyUtilClient import AssemblyUtil as _AssClient
from installed_clients.DataFileUtilClient import DataFileUtil as _DFUClient
from installed_clients.KBaseReportClient import KBaseReport as _KBRepClient
from installed_clients.WorkspaceClient import Workspace as _WSClient
from installed_clients.baseclient import ServerError as _AssError
from installed_clients.baseclient import ServerError as _DFUError
from installed_clients.baseclient import ServerError as _RepError
from installed_clients.baseclient import ServerError as _WSError


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
        self.ref = str(self.wsid) + '/' + str(self.id) + '/' + str(self.version)
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
    VERSION = "0.0.6"
    GIT_URL = "https://github.com/kbaseapps/kb_quast.git"
    GIT_COMMIT_HASH = "8d29af55af662fa41442c0134dd90c45decd8cf4"

    #BEGIN_CLASS_HEADER

    THREADS_PER_CORE = 1
    TWENTY_MB = 20 * 1024 * 1024
    # Same as Quast: http://quast.sourceforge.net/docs/manual.html#sec2.3
    DEFAULT_MIN_CONTIG_LENGTH = 500
    # Per the KBase SME slack channel, 50 is an appropriate lower bound
    MINIMUM_MIN_CONTIG_LENGTH = 50

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

    def get_min_contig_length(self, params):
        mcl = params.get('min_contig_length')
        mcl = self.DEFAULT_MIN_CONTIG_LENGTH if mcl is None else mcl
        if type(mcl) != int or mcl < self.MINIMUM_MIN_CONTIG_LENGTH:
            raise ValueError("Minimum contig length must be an integer >= {}, got: {}"
                             .format(self.MINIMUM_MIN_CONTIG_LENGTH, mcl))
        return mcl

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
        for i in info:  # don't check type - assemblyutils should handle that
            self.log('{}/{} {} {}'.format(i.workspace, i.name, i.ref, i.type))
        absrefs = [i.ref for i in info]
        if len(set(absrefs)) != len(absrefs):
            raise ValueError('Duplicate objects detected in input')  # could list objs later
        return info

    def run_quast_exec(self, outdir, filepaths, labels, min_contig_length, skip_glimmer=False):
        threads = psutil.cpu_count() * self.THREADS_PER_CORE
        # DO NOT use genemark instead of glimmer, not open source
        # DO NOT use metaQUAST, uses SILVA DB which is not open source
        cmd = (['quast.py',
                '--threads', str(threads),
                '-o', outdir,
                '--labels', ','.join(labels),
                '--min-contig', str(min_contig_length),
                '--glimmer',
                '--contig-thresholds', '0,1000,10000,100000,1000000']
               + filepaths)

        if skip_glimmer:
            self.log('skipping glimmer due to large input file(s)')
            cmd.remove('--glimmer')

        self.log('running QUAST with command line ' + str(cmd))
        retcode = _subprocess.call(cmd)
        self.log('QUAST return code: ' + str(retcode))
        if retcode:
            # can't actually figure out how to test this. Give quast garbage it skips the file.
            # Give quast a file with a missing sequence it acts completely normally.
            raise ValueError('QUAST reported an error, return code was ' + str(retcode))
        # quast will ignore bad files and keep going, which is a disaster for
        # reproducibility and accuracy if you're not watching the logs like a hawk.
        # for now use this hack to check that all files were processed. Maybe there's a better way.
        with open(_os.path.join(outdir, 'report.tsv'), 'r') as f:
            files_proc = len(f.readline().split('\t')) - 1
        files_exp = len(filepaths)
        if files_proc != files_exp:
            err = ('QUAST skipped some files - {} expected, {} processed.'
                   .format(files_exp, files_proc))
            self.log(err)
            raise ValueError(err)

    def check_large_input(self, filepaths):
        skip_glimmer = False
        basecount = 0
        for filepath in filepaths:
            for record in _SeqIO.parse(filepath, 'fasta'):
                basecount += len(record.seq)

        if basecount > self.TWENTY_MB:
            skip_glimmer = True

        return skip_glimmer

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
        :param params: instance of type "QUASTAppParams" (Input for running
           QUAST as a Narrative application. workspace_name - the name of the
           workspace where the KBaseReport object will be saved. assemblies -
           the list of assemblies upon which QUAST will be run. force_glimmer
           - running '--glimmer' option regardless of assembly object size)
           -> structure: parameter "workspace_name" of String, parameter
           "assemblies" of list of type "assembly_ref" (An X/Y/Z style
           reference to a workspace object containing an assembly, either a
           KBaseGenomes.ContigSet or KBaseGenomeAnnotations.Assembly.),
           parameter "force_glimmer" of type "boolean" (A boolean - 0 for
           false, 1 for true. @range (0, 1))
        :returns: instance of type "QUASTAppOutput" (Output of the
           run_quast_app function. report_name - the name of the
           KBaseReport.Report workspace object. report_ref - the workspace
           reference of the report.) -> structure: parameter "report_name" of
           String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_QUAST_app
        wsname = params.get('workspace_name')  # TODO take wsid when possible
        if not wsname:
            raise ValueError('No workspace name provided')
        params['make_handle'] = 0
        quastret = self.run_QUAST(ctx, params)[0]
        with open(_os.path.join(quastret['quast_path'], 'report.txt')) as reportfile:
            report = reportfile.read()
        kbr = _KBRepClient(self.callback_url)
        self.log('Saving QUAST report')
        try:
            repout = kbr.create_extended_report(
                {'message': report,
                 'direct_html_link_index': 0,
                 'html_links': [{'shock_id': quastret['shock_id'],
                                 'name': 'report.html',
                                 'label': 'QUAST report'}
                                ],
                 'report_object_name': 'kb_quast_report_' + str(_uuid.uuid4()),
                 'workspace_name': wsname
                 })
        except _RepError as re:
            self.log('Logging exception from creating report object')
            self.log(str(re))
            # TODO delete shock node
            raise
        output = {'report_name': repout['name'],
                  'report_ref': repout['ref']
                  }
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
           be run. Optional arguments: make_handle - create a handle for the
           new shock node for the report. force_glimmer - running '--glimmer'
           option regardless of file/assembly object size) -> structure:
           parameter "assemblies" of list of type "assembly_ref" (An X/Y/Z
           style reference to a workspace object containing an assembly,
           either a KBaseGenomes.ContigSet or
           KBaseGenomeAnnotations.Assembly.), parameter "files" of list of
           type "FASTAFile" (A local FASTA file. path - the path to the FASTA
           file. label - the label to use for the file in the QUAST output.
           If missing, the file name will be used.) -> structure: parameter
           "path" of String, parameter "label" of String, parameter
           "make_handle" of type "boolean" (A boolean - 0 for false, 1 for
           true. @range (0, 1)), parameter "force_glimmer" of type "boolean"
           (A boolean - 0 for false, 1 for true. @range (0, 1))
        :returns: instance of type "QUASTOutput" (Ouput of the run_quast
           function. shock_id - the id of the shock node where the zipped
           QUAST output is stored. handle - the new handle for the shock
           node, if created. node_file_name - the name of the file stored in
           Shock. size - the size of the file stored in shock. quast_path -
           the directory containing the quast output and the zipfile of the
           directory.) -> structure: parameter "shock_id" of String,
           parameter "handle" of type "Handle" (A handle for a file stored in
           Shock. hid - the id of the handle in the Handle Service that
           references this shock node id - the id for the shock node url -
           the url of the shock server type - the type of the handle. This
           should always be shock. file_name - the name of the file
           remote_md5 - the md5 digest of the file.) -> structure: parameter
           "hid" of String, parameter "file_name" of String, parameter "id"
           of String, parameter "url" of String, parameter "type" of String,
           parameter "remote_md5" of String, parameter "node_file_name" of
           String, parameter "size" of String, parameter "quast_path" of
           String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_QUAST
        self.log('Starting QUAST run. Parameters:')
        self.log(str(params))
        assemblies = params.get('assemblies')
        files = params.get('files')
        min_contig_length = self.get_min_contig_length(params)  # fail early if param is bad
        if not self.xor(assemblies, files):
            raise ValueError(
                'One and only one of a list of assembly references or files is required')
        tdir = _os.path.join(self.scratch, str(_uuid.uuid4()))
        self.mkdir_p(tdir)
        if assemblies:
            if type(assemblies) != list:
                raise ValueError('assemblies must be a list')
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

        if params.get('force_glimmer'):
            skip_glimmer = False
        else:
            skip_glimmer = self.check_large_input(filepaths)

        out = _os.path.join(tdir, 'quast_results')
        # TODO check for name duplicates in labels and do something about it
        self.run_quast_exec(out, filepaths, labels, min_contig_length, skip_glimmer)
        dfu = _DFUClient(self.callback_url)
        try:
            mh = params.get('make_handle')
            output = dfu.file_to_shock({'file_path': out,
                                        'make_handle': 1 if mh else 0,
                                        'pack': 'zip'})
        except _DFUError as dfue:
            # not really any way to test this block
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
