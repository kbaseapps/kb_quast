/*
Wrapper for the QUAST tool. Takes one or more assemblies as input and produces a QUAST report
stored in a zip file in Shock.
*/

module kb_quast {

	/* An X/Y/Z style reference to a workspace object containing an assembly, either a
		KBaseGenomes.ContigSet or KBaseGenomeAnnotations.Assembly.
	*/
	typedef string assembly_ref;

	/* Input for running QUAST.
		assemblies - the list of assemblies upon which QUAST will be run.
	*/
	typedef structure {
		list<assembly_ref> assemblies;
	} QUASTParams;
	
	/* Output of the run_quast_app function.
		report_name - the name of the KBaseReport.Report workspace object.
		report_ref - the workspace reference of the report.
	*/
	typedef structure {
		string report_name;
		string report_ref;
	} QUASTAppOutput;

	/* Run QUAST and save a KBaseReport with the output. */
	funcdef run_QUAST_app(QUASTParams params) returns(QUASTAppOutput output)
		authentication required;
		
	/* Ouput of the run_quast function.
		shock_node - the id of the shock node where the zipped QUAST output is stored.
	*/
	typedef structure {
		string shock_node;
	} QUASTOutput;
	
	/* Run QUAST and return a shock node containing the zipped QUAST output. */
	funcdef run_QUAST(QUASTParams params) returns(QUASTOutput output) authentication required;

};
