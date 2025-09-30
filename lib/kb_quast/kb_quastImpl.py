# -*- coding: utf-8 -*-
#BEGIN_HEADER
import errno as _errno
import os as _os
import subprocess as _subprocess
import time as _time
import uuid as _uuid
import shlex  # kept from original (not used directly but harmless)
from pathlib import Path  # kept from original (not used directly but harmless)

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
#END_HEADER


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
    VERSION = "1.1.0"
    GIT_URL = "https://github.com/kbaseapps/kb_quast"
    GIT_COMMIT_HASH = "f6be7c27bbf44a0d65b0250dbdb8079b5df9d7ae"

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
        # would be nice if the assembly utils had bulk download...
        for i in object_infos:
            fn = _os.path.join(target_dir, i.ref.replace('/', '_'))
            filepaths.append(fn)
            self.log('getting assembly from object {} and storing at {}'.format(i.ref, fn))
            try:
                asscli.get_assembly_as_fasta({'ref': i.ref, 'filename': fn})
            except _AssError as asserr:
                self.log('Logging assembly downloader exception')
                self.log(str(asserr))
                raise asserr
        return filepaths

    def get_assembly_object_info(self, assemblies, token):
        # Prefer the top-level ObjInfo; fall back to a local definition if missing
        ObjInfoClass = globals().get('ObjInfo')
        if ObjInfoClass is None:
            class ObjInfoClass(object):
                def __init__(self, obj_info):
                    self.id = obj_info[0]
                    self.name = obj_info[1]
                    t_full = obj_info[2]
                    self.type, self.type_ver = (t_full.split('-', 1) + [''])[:2] if '-' in t_full else (t_full, '')
                    self.time = obj_info[3]
                    self.version = obj_info[4]
                    self.saved_by = obj_info[5]
                    self.wsid = obj_info[6]
                    self.workspace = obj_info[7]
                    self.chsum = obj_info[8]
                    self.size = obj_info[9]
                    self.meta = obj_info[10]
                    self.ref = f"{self.wsid}/{self.id}/{self.version}"

        refs = [{'ref': x} for x in assemblies]
        ws = _WSClient(self.ws_url, token=token)
        self.log('Getting object information from workspace')

        try:
            infos = ws.get_object_info3({'objects': refs})['infos']
        except _WSError as wse:
            self.log('Logging workspace exception')
            self.log(str(wse))
            raise wse

        info = [ObjInfoClass(i) for i in infos]

        self.log('Object list:')
        for o in info:
            self.log(f'{o.workspace}/{o.name} {o.ref} {o.type}')

        absrefs = [o.ref for o in info]
        if len(set(absrefs)) != len(absrefs):
            raise ValueError('Duplicate objects detected in input')
        return info

    def expand_assembly_sets(self, set_refs, token):
        """
        Given a list of KBaseSets.AssemblySet refs, return a flat list of assembly refs.
        Supports common schemas: {'items': [{'ref': ...}, ...]} or {'elements': [{'ref': ...}, ...]}.
        """
        if not set_refs:
            return []
        ws = _WSClient(self.ws_url, token=token)
        objs = ws.get_objects2({'objects': [{'ref': r} for r in set_refs]})['data']
        out = []
        for od in objs:
            data = od.get('data', {}) or {}
            items = data.get('items')
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and it.get('ref'):
                        out.append(it['ref'])
                continue
            elements = data.get('elements')
            if isinstance(elements, list):
                for el in elements:
                    if isinstance(el, dict) and el.get('ref'):
                        out.append(el['ref'])
                continue
        return out

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
            raise ValueError('QUAST reported an error, return code was ' + str(retcode))
        # check that all files were processed
        with open(_os.path.join(outdir, 'report.tsv'), 'r') as f:
            files_proc = len(f.readline().split('\t')) - 1
        files_exp = len(filepaths)
        if files_proc != files_exp:
            err = ('QUAST skipped some files - {} expected, {} processed.'
                   .format(files_exp, files_proc))
            self.log(err)
            raise ValueError(err)


    # ---------- NEW HELPERS (instance methods) ----------
    def _ws_batch_get_info(self, ws_client, refs):

        """
        Batched get_object_info3 to avoid repeated roundtrips.
        Returns list of dicts with keys: ref, type
        """
        if not refs:
            return []
        info = ws_client.get_object_info3({"objects": [{"ref": r} for r in refs]})["infos"]
        out = []
        for r, i in zip(refs, info):
            out.append({"ref": r, "type": i[2]})
        return out

    def _classify_input_refs(self, ws_client, raw_refs):
        """
        Split mixed refs into assemblies vs assembly_sets based on WS type.
        Returns (assemblies, assembly_sets).
        """
        assemblies, assembly_sets = [], []
        for item in self._ws_batch_get_info(ws_client, raw_refs):
            t = item["type"] or ""
            t_base = t.split("-", 1)[0]  # strip version suffix
            if t_base in ("KBaseGenomes.Assembly", "KBaseGenomeAnnotations.Assembly"):
                assemblies.append(item["ref"])
            elif t_base == "KBaseSets.AssemblySet":
                assembly_sets.append(item["ref"])
            else:
                raise ValueError(
                    f"Unsupported input ref type: {t} for {item['ref']}. "
                    "Expected KBaseGenomes.Assembly or KBaseSets.AssemblySet."
                )
        return assemblies, assembly_sets

    def _gather_inputs(self, params, _ws_client_unused):
        """
        Validate & normalize raw params **without calling WS**.
        Accepts:
        - params['assemblies']      (list<ref> or absent)
        - params['assembly_sets']   (list<ref> or absent)
        - params['files']           (list<{path,label}> or absent)
        Returns dict with lists; raises ValueError on bad types.
        """
        assemblies = params.get("assemblies", [])
        assembly_sets = params.get("assembly_sets", [])
        files = params.get("files", [])

        if assemblies is None: assemblies = []
        if assembly_sets is None: assembly_sets = []
        if files is None: files = []

        if not isinstance(assemblies, list):
            raise ValueError('assemblies must be a list')
        if not isinstance(assembly_sets, list):
            raise ValueError('assembly_sets must be a list')
        if not isinstance(files, list):
            raise ValueError('files must be a list')

        # Enforce the “one and only one” rule here so we never hit WS on bad combos
        has_obj_inputs = bool(assemblies or assembly_sets)
        if bool(files) == has_obj_inputs:
            raise ValueError('One and only one of a list of assembly references or files is required')

        return {"assemblies": assemblies, "assembly_sets": assembly_sets, "files": files}

    # ---------- END HELPERS ----------

    def check_large_input(self, filepaths):
        skip_glimmer = False
        basecount = 0
        for filepath in filepaths:
            for record in _SeqIO.parse(filepath, 'fasta'):
                basecount += len(record.seq)

        if basecount > self.TWENTY_MB:
            skip_glimmer = True

        return skip_glimmer

    # --------- NEW: metaquast runner ----------
    def run_metaquast_exec(self, outdir, filepaths, labels, mparams, ref_paths=None, refs_txt_path=None):
        """
        Build and run metaquast.py with supplied inputs.
        mparams: dict with keys:
          min_contig_length, min_identity, min_alignment, max_ref_num,
          unique_mapping ('0'/'1'), reuse_combined_alignments ('0'/'1'),
          disable_icarus ('0'/'1'), no_krona ('0'/'1'), threads (int)
        ref_paths: list of reference FASTA paths (optional)
        refs_txt_path: path to references.txt for --references-list (optional)
        """
        threads = int(mparams.get('threads', psutil.cpu_count() * self.THREADS_PER_CORE))
        cmd = [
            'metaquast.py',
            '--threads', str(threads),
            '-o', outdir,
            '--min-contig', str(int(mparams.get('min_contig_length', self.DEFAULT_MIN_CONTIG_LENGTH))),
            '--min-identity', str(float(mparams.get('min_identity', 90))),
            '--min-alignment', str(int(mparams.get('min_alignment', 65)))
        ]

        if mparams.get('unique_mapping', '0') == '1':
            cmd.append('--unique-mapping')
        if mparams.get('reuse_combined_alignments', '1') == '1':
            cmd.append('--reuse-combined-alignments')
        if mparams.get('disable_icarus', '0') == '1':
            cmd.append('--no-icarus')
        if mparams.get('no_krona', '0') == '1':
            cmd.append('--no-krona')

        if labels:
            cmd += ['-l', ','.join(labels)]

        # references
        if ref_paths:
            cmd += ['-r', ','.join(ref_paths)]
        if refs_txt_path:
            cmd += ['--references-list', refs_txt_path]

        # (autodetect handled by caller by just omitting refs and adding --max-ref-num)
        if 'max_ref_num' in mparams and str(mparams.get('max_ref_num', '')).strip() != '':
            cmd += ['--max-ref-num', str(int(mparams['max_ref_num']))]

        cmd += filepaths

        self.log('running MetaQUAST with command line ' + str(cmd))
        retcode = _subprocess.call(cmd)
        self.log('MetaQUAST return code: ' + str(retcode))
        if retcode:
            raise ValueError('MetaQUAST reported an error, return code was ' + str(retcode))

        # Light sanity check: ensure a report exists somewhere
        candidate_paths = [
            _os.path.join(outdir, 'combined_reference', 'report.tsv'),
            _os.path.join(outdir, 'report.tsv')
        ]
        if not any(_os.path.exists(p) for p in candidate_paths):
            raise ValueError('MetaQUAST finished but no report.tsv was found in output.')

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
           - running '--glimmer' option regardless of assembly object size
           min_contig_length - set the minimum size of contigs to process.
           Defaults to 500, minimum allowed is 50.) -> structure: parameter
           "workspace_name" of String, parameter "assemblies" of list of type
           "assembly_ref" (An X/Y/Z style reference to a workspace object
           containing an assembly, either a KBaseGenomes.ContigSet or
           KBaseGenomeAnnotations.Assembly.), parameter "force_glimmer" of
           type "boolean" (A boolean - 0 for false, 1 for true. @range (0,
           1)), parameter "min_contig_length" of Long
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
            raise re
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
        Supports:
          - files: list of {'path', 'label'}
          - assemblies: list<ref> to Assembly/ContigSet
          - assembly_sets: list<ref> to KBaseSets.AssemblySet
        Exactly one of (files) or (assemblies/assembly_sets) must be provided.
        :param params: instance of type "QUASTParams" (Input for running
           QUAST. assemblies - the list of assemblies upon which QUAST will
           be run. -OR- files - the list of FASTA files upon which QUAST will
           be run. Optional arguments: make_handle - create a handle for the
           new shock node for the report. force_glimmer - running '--glimmer'
           option regardless of file/assembly object size min_contig_length -
           set the minimum size of contigs to process. Defaults to 500,
           minimum allowed is 50.) -> structure: parameter "assemblies" of
           list of type "assembly_ref" (An X/Y/Z style reference to a
           workspace object containing an assembly, either a
           KBaseGenomes.ContigSet or KBaseGenomeAnnotations.Assembly.),
           parameter "files" of list of type "FASTAFile" (A local FASTA file.
           path - the path to the FASTA file. label - the label to use for
           the file in the QUAST output. If missing, the file name will be
           used.) -> structure: parameter "path" of String, parameter "label"
           of String, parameter "make_handle" of type "boolean" (A boolean -
           0 for false, 1 for true. @range (0, 1)), parameter "force_glimmer"
           of type "boolean" (A boolean - 0 for false, 1 for true. @range (0,
           1)), parameter "min_contig_length" of Long
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
           "remote_md5" of String, parameter "node_file_name" of
           String, parameter "size" of String, parameter "quast_path" of
           String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_QUAST
        self.log('Starting QUAST run. Parameters:')
        self.log(str(params))

        # Normalize inputs (classify mixed refs into assemblies vs assembly_sets)
        ws = _WSClient(self.ws_url, token=ctx['token'])
        normalized = self._gather_inputs(params, ws)
        assemblies = normalized["assemblies"]
        assembly_sets = normalized["assembly_sets"]
        files = normalized["files"]

        # NEW: reclassify anything in `assemblies` that's actually an AssemblySet
        if assemblies:
            infos = self._ws_batch_get_info(ws, assemblies)
            asm_ok, set_found, bad = [], [], []
            for it in infos:
                tbase = (it['type'] or '').split('-', 1)[0]
                if tbase in ('KBaseGenomes.Assembly', 'KBaseGenomeAnnotations.Assembly'):
                    asm_ok.append(it['ref'])
                elif tbase == 'KBaseSets.AssemblySet':
                    set_found.append(it['ref'])
                else:
                    bad.append((it['ref'], it['type']))
            if bad:
                raise ValueError(
                    'Unsupported input ref type(s): ' +
                    ', '.join([f'{r} ({t})' for r, t in bad]) +
                    '. Expected Assembly or AssemblySet.'
                )
            assemblies = asm_ok
            assembly_sets = list(dict.fromkeys(list(assembly_sets) + set_found))

        min_contig_length = self.get_min_contig_length(params)  # fail early if param is bad

        has_obj_inputs = bool(assemblies or assembly_sets)
        if bool(files) == has_obj_inputs:
            raise ValueError('One and only one of a list of assembly references or files is required')

        tdir = _os.path.join(self.scratch, str(_uuid.uuid4()))
        self.mkdir_p(tdir)

        if has_obj_inputs:
            if type(assemblies) != list:
                raise ValueError('assemblies must be a list')
            if type(assembly_sets) != list:
                raise ValueError('assembly_sets must be a list')

            # Expand sets to assembly refs and combine
            set_expanded = self.expand_assembly_sets(assembly_sets, ctx['token']) if assembly_sets else []
            all_ass_refs = list(assemblies) + set_expanded
            if not all_ass_refs:
                raise ValueError('Provided assembly_sets expand to zero assemblies')

            info = self.get_assembly_object_info(all_ass_refs, ctx['token'])
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
            self.log('Logging exception loading results to shock')
            self.log(str(dfue))
            raise dfue
        output['quast_path'] = out
        #END run_QUAST

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_QUAST return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    # -------- NEW: MetaQUAST (service) --------
    def run_MetaQUAST(self, ctx, params):
        """
        Run MetaQUAST and return a shock node containing the zipped output.
        Inputs mirror the app form:
          assemblies: list<ref> (Assembly or AssemblySet allowed via expand)
          reference_mode: 'none' | 'assemblyset' | 'accession_list' | 'autodetect'
          reference_set: ref to KBaseSets.AssemblySet (if mode=assemblyset)
          accession_list: string with one accession per line (if mode=accession_list)
          min_contig_length, min_identity, min_alignment, max_ref_num
          unique_mapping ('0'/'1'), reuse_combined_alignments ('0'/'1'),
          disable_icarus ('0'/'1'), no_krona ('0'/'1'), disable_downloads ('0'/'1')
          threads
        """
        self.log('Starting MetaQUAST run. Parameters:')
        self.log(str(params))

        ws = _WSClient(self.ws_url, token=ctx['token'])

        # Normalize target assemblies
        normalized = self._gather_inputs(params, ws)
        assemblies = normalized["assemblies"]
        assembly_sets = normalized["assembly_sets"]
        files = normalized["files"]

        # NEW: reclassify anything in `assemblies` that's actually an AssemblySet
        if assemblies:
            infos = self._ws_batch_get_info(ws, assemblies)
            asm_ok, set_found, bad = [], [], []
            for it in infos:
                tbase = (it['type'] or '').split('-', 1)[0]
                if tbase in ('KBaseGenomes.Assembly', 'KBaseGenomeAnnotations.Assembly'):
                    asm_ok.append(it['ref'])
                elif tbase == 'KBaseSets.AssemblySet':
                    set_found.append(it['ref'])
                else:
                    bad.append((it['ref'], it['type']))
            if bad:
                raise ValueError(
                    'Unsupported input ref type(s): ' +
                    ', '.join([f'{r} ({t})' for r, t in bad]) +
                    '. Expected Assembly or AssemblySet.'
                )
            assemblies = asm_ok
            assembly_sets = list(dict.fromkeys(list(assembly_sets) + set_found))

        if bool(files) == bool(assemblies or assembly_sets):
            raise ValueError('One and only one of a list of assembly references or files is required')

        tdir = _os.path.join(self.scratch, str(_uuid.uuid4()))
        self.mkdir_p(tdir)

        # Download input assemblies to fasta paths + labels
        if assemblies or assembly_sets:
            set_expanded = self.expand_assembly_sets(assembly_sets, ctx['token']) if assembly_sets else []
            all_ass_refs = list(assemblies) + set_expanded
            if not all_ass_refs:
                raise ValueError('Provided assembly_sets expand to zero assemblies')
            info = self.get_assembly_object_info(all_ass_refs, ctx['token'])
            asm_paths = self.get_assemblies(tdir, info)
            labels = [i.name for i in info]
        else:
            # files path mode (rare for MetaQUAST, but supported)
            asm_paths = []
            labels = []
            for i, lp in enumerate(files):
                p = lp.get('path'); l = lp.get('label')
                if not _os.path.isfile(p):
                    raise ValueError('File entry {}, {}, is not a file'.format(i + 1, p))
                asm_paths.append(p); labels.append(l if l else _os.path.basename(p))

        # References per mode
        ref_mode = params.get('reference_mode', 'none')
        disable_downloads = params.get('disable_downloads', '0') == '1'

        ref_paths = None
        refs_txt = None

        if ref_mode == 'assemblyset':
            rset = params.get('reference_set')
            if not rset:
                raise ValueError('reference_mode is assemblyset but no reference_set provided')
            # Expand & download the reference set to local FASTAs
            ref_refs = self.expand_assembly_sets([rset], ctx['token'])
            if not ref_refs:
                raise ValueError('reference_set expands to zero assemblies')
            rinfo = self.get_assembly_object_info(ref_refs, ctx['token'])
            ref_paths = self.get_assemblies(tdir, rinfo)

        elif ref_mode == 'accession_list':
            acc_text = (params.get('accession_list') or '').strip()
            if not acc_text:
                raise ValueError('reference_mode is accession_list but accession_list is empty')
            refs_txt = _os.path.join(tdir, 'references.txt')
            with open(refs_txt, 'w') as fh:
                fh.write(acc_text + '\n')

        elif ref_mode == 'autodetect':
            if disable_downloads:
                raise ValueError('Autodetect requires downloads; disable_downloads is set.')
            # No files to prepare; metaquast will BLAST, fetch refs, and honor --max-ref-num

        elif ref_mode == 'none':
            pass
        else:
            raise ValueError('Unknown reference_mode: ' + str(ref_mode))

        # Output dir
        outdir = _os.path.join(tdir, 'metaquast_results')

        # Build + run
        self.run_metaquast_exec(
            outdir=outdir,
            filepaths=asm_paths,
            labels=labels,
            mparams=params,
            ref_paths=ref_paths,
            refs_txt_path=refs_txt
        )

        # Package to Shock
        dfu = _DFUClient(self.callback_url)
        try:
            mh = params.get('make_handle')
            output = dfu.file_to_shock({
                'file_path': outdir,
                'make_handle': 1 if mh else 0,
                'pack': 'zip'
            })
        except _DFUError as dfue:
            self.log('Logging exception loading MetaQUAST results to shock')
            self.log(str(dfue))
            raise dfue

        output['metaquast_path'] = outdir
        return [output]

    def run_MetaQUAST_app(self, ctx, params):
        """
        App wrapper: runs MetaQUAST and saves a KBaseReport with HTML + zip link.
        Parameter names match the Narrative method spec.
        """
        wsname = params.get('workspace_name')
        if not wsname:
            raise ValueError('No workspace name provided')

        # Ensure we don't create handles by default from app context
        params = dict(params)
        params['make_handle'] = 0

        mret = self.run_MetaQUAST(ctx, params)[0]

        # Prefer combined_reference/report.html if present; otherwise report.html
        # We upload only the zip via Shock and link to report.html (consistent with run_QUAST_app).
        kbr = _KBRepClient(self.callback_url)
        self.log('Saving MetaQUAST report')
        try:
            repout = kbr.create_extended_report(
                {
                    'message': 'MetaQUAST finished.',
                    'direct_html_link_index': 0,
                    'html_links': [{
                        'shock_id': mret['shock_id'],
                        'name': 'report.html',
                        'label': 'MetaQUAST report'
                    }],
                    'file_links': [{
                        'shock_id': mret['shock_id'],
                        'name': 'metaquast_results.zip',
                        'label': 'MetaQUAST results (zip)'
                    }],
                    'report_object_name': 'kb_metaquast_report_' + str(_uuid.uuid4()),
                    'workspace_name': wsname
                }
            )
        except _RepError as re:
            self.log('Logging exception from creating MetaQUAST report object')
            self.log(str(re))
            raise re

        # --- 2nd option: define `output` then keep the guard/return ---
        output = {'report_name': repout['name'], 'report_ref': repout['ref']}
        if not isinstance(output, dict):
            raise ValueError('Method run_MetaQUAST_app return value output is not type dict as required.')
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
