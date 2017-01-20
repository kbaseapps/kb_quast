/*
Wrapper for the QUAST tool. Takes one or more assemblies as input and produces a QUAST report
stored in a zip file in Shock.
*/

module kb_quast {

	/* An X/Y/Z style reference to a workspace object containing an assembly, either a
		KBaseGenomes.ContigSet or KBaseGenomeAnnotations.Assembly.
	*/
	typedef string assembly_ref;
	
	/* A handle for a file stored in Shock.
		hid - the id of the handle in the Handle Service that references this shock node
		id - the id for the shock node
		url - the url of the shock server
		type - the type of the handle. This should always be shock.
		file_name - the name of the file
		remote_md5 - the md5 digest of the file.
	*/
	typedef structure {
		string hid;
		string file_name;
		string id;
		string url;
		string type;
		string remote_md5;
	} Handle;
	
	/* A local FASTA file.
		path - the path to the FASTA file.
		label - the label to use for the file in the QUAST output. If missing, the file name will
		be used.
	*/
	typedef structure {
		string path;
		string label;
	} FASTAFile;

	/* Input for running QUAST as a Narrative application.
		workspace_name - the name of the workspace where the KBaseReport object will be saved.
		assemblies - the list of assemblies upon which QUAST will be run.
	*/
	typedef structure {
		string workspace_name;
		list<assembly_ref> assemblies;
	} QUASTAppParams;
	
	/* Output of the run_quast_app function.
		report_name - the name of the KBaseReport.Report workspace object.
		report_ref - the workspace reference of the report.
	*/
	typedef structure {
		string report_name;
		string report_ref;
	} QUASTAppOutput;

	/* Run QUAST and save a KBaseReport with the output. */
	funcdef run_QUAST_app(QUASTAppParams params) returns(QUASTAppOutput output)
		authentication required;
	
	/* Input for running QUAST.
		assemblies - the list of assemblies upon which QUAST will be run.
		-OR-
		files - the list of FASTA files upon which QUAST will be run.
	*/
	typedef structure {
		list<assembly_ref> assemblies;
		list<FASTAFile> files;
	} QUASTParams;
	
	/* Ouput of the run_quast function.
		shock_id - the id of the shock node where the zipped QUAST output is stored.
		handle - the new handle for the shock node.
		node_file_name - the name of the file stored in Shock.
		size - the size of the file stored in shock.
		quast_path - the directory containing the quast output and the zipfile of the directory.
	*/
	typedef structure {
		string shock_id;
		Handle handle;
		string node_file_name;
		string size;
		string quast_path;
	} QUASTOutput;
	
	/* Run QUAST and return a shock node containing the zipped QUAST output. */
	funcdef run_QUAST(QUASTParams params) returns(QUASTOutput output) authentication required;

};
