/*
Wrapper for the QUAST tool. Takes one or more assemblies as input and produces a QUAST report
stored in a zip file in Shock.
*/

module kb_quast {

    /* A boolean - 0 for false, 1 for true.
       @range (0, 1)
    */
    typedef int boolean;

    /* Workspace refs */
    typedef string assembly_ref;        /* Assembly / ContigSet */
    typedef string assemblyset_ref;     /* KBaseSets.AssemblySet */
    typedef string reads_ref;           /* for future read-based options */

    /* A handle for a file stored in Shock. */
    typedef structure {
        string hid;
        string file_name;
        string id;
        string url;
        string type;
        string remote_md5;
    } Handle;

    /* A local FASTA file. */
    typedef structure {
        string path;
        string label;
    } FASTAFile;

    /**********************
     * QUAST (app-level)
     **********************/

    /* Input for running QUAST as a Narrative application. */
    typedef structure {
        string workspace_name;
        list<assembly_ref> assemblies;

        boolean force_glimmer;
        int     min_contig_length;

        /* Extra knobs from UI (kept optional so mapping validates) */
        boolean use_large_genome_mode;
        boolean enable_kmer_stats;
        int     kmer_size;
        boolean simulate_upper_bound;
        int     upper_bound_min_con;
        int     est_insert_size;
        boolean disable_icarus;
        boolean report_all_metrics;
        reads_ref reads_pe_ref;
        reads_ref reads_nanopore_ref;
        reads_ref reads_pacbio_ref;
        int     threads;
    } QUASTAppParams;
    /* @optional QUASTAppParams.force_glimmer QUASTAppParams.min_contig_length
       QUASTAppParams.use_large_genome_mode QUASTAppParams.enable_kmer_stats
       QUASTAppParams.kmer_size QUASTAppParams.simulate_upper_bound
       QUASTAppParams.upper_bound_min_con QUASTAppParams.est_insert_size
       QUASTAppParams.disable_icarus QUASTAppParams.report_all_metrics
       QUASTAppParams.reads_pe_ref QUASTAppParams.reads_nanopore_ref
       QUASTAppParams.reads_pacbio_ref QUASTAppParams.threads */

    /* Output of the run_quast_app function. */
    typedef structure {
        string report_name;
        string report_ref;
    } QUASTAppOutput;

    /* Run QUAST and save a KBaseReport with the output. */
    funcdef run_QUAST_app(QUASTAppParams params) returns (QUASTAppOutput output)
        authentication required;

    /**********************
     * QUAST (service)
     **********************/

    /* Input for running QUAST (service-level). */
    typedef structure {
        list<assembly_ref> assemblies;
        list<FASTAFile>    files;

        boolean make_handle;
        boolean force_glimmer;
        int     min_contig_length;
    } QUASTParams;
    /* @optional QUASTParams.make_handle QUASTParams.force_glimmer QUASTParams.min_contig_length */

    /* Output of the run_quast function. */
    typedef structure {
        string shock_id;
        Handle handle;
        string node_file_name;
        string size;
        string quast_path;
    } QUASTOutput;

    /* Run QUAST and return a shock node containing the zipped QUAST output. */
    funcdef run_QUAST(QUASTParams params) returns (QUASTOutput output)
        authentication required;

    /**********************
     * MetaQUAST (app-level)
     **********************/

    /* Input for running MetaQUAST as a Narrative application. */
    typedef structure {
        string workspace_name;
        list<assembly_ref> assemblies;

        /* reference handling */
        string          reference_mode;    /* "none" | "assemblyset" | "accession_list" | "autodetect" */
        assemblyset_ref reference_set;     /* when reference_mode = "assemblyset" */
        string          accession_list;    /* when reference_mode = "accession_list" */

        /* run knobs */
        int     min_contig_length;         /* default 500 */
        float   min_identity;              /* default 90 */
        int     min_alignment;             /* default 65 */
        int     max_ref_num;               /* used only for autodetect */
        boolean unique_mapping;            /* 0/1 */
        boolean reuse_combined_alignments; /* 0/1 */
        boolean disable_icarus;            /* 0/1 -> --no-icarus */
        boolean no_krona;                  /* 0/1 -> --no-krona */
        boolean disable_downloads;         /* 0/1 (blocks autodetect) */
        int     threads;                   /* default 8 */
    } MetaQUASTAppParams;
    /* @optional MetaQUASTAppParams.reference_mode MetaQUASTAppParams.reference_set
       MetaQUASTAppParams.accession_list MetaQUASTAppParams.min_contig_length
       MetaQUASTAppParams.min_identity MetaQUASTAppParams.min_alignment
       MetaQUASTAppParams.max_ref_num MetaQUASTAppParams.unique_mapping
       MetaQUASTAppParams.reuse_combined_alignments MetaQUASTAppParams.disable_icarus
       MetaQUASTAppParams.no_krona MetaQUASTAppParams.disable_downloads
       MetaQUASTAppParams.threads */

    /* Output of the run_metaquast_app function. */
    typedef structure {
        string report_name;
        string report_ref;
    } MetaQUASTAppOutput;

    /* Run MetaQUAST and save a KBaseReport with the output. */
    funcdef run_MetaQUAST_app(MetaQUASTAppParams params) returns (MetaQUASTAppOutput output)
        authentication required;

};
