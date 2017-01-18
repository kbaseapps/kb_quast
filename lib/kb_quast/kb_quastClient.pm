package kb_quast::kb_quastClient;

use JSON::RPC::Client;
use POSIX;
use strict;
use Data::Dumper;
use URI;
use Bio::KBase::Exceptions;
my $get_time = sub { time, 0 };
eval {
    require Time::HiRes;
    $get_time = sub { Time::HiRes::gettimeofday() };
};

use Bio::KBase::AuthToken;

# Client version should match Impl version
# This is a Semantic Version number,
# http://semver.org
our $VERSION = "0.1.0";

=head1 NAME

kb_quast::kb_quastClient

=head1 DESCRIPTION


Wrapper for the QUAST tool. Takes one or more assemblies as input and produces a QUAST report
stored in a zip file in Shock.


=cut

sub new
{
    my($class, $url, @args) = @_;
    

    my $self = {
	client => kb_quast::kb_quastClient::RpcClient->new,
	url => $url,
	headers => [],
    };

    chomp($self->{hostname} = `hostname`);
    $self->{hostname} ||= 'unknown-host';

    #
    # Set up for propagating KBRPC_TAG and KBRPC_METADATA environment variables through
    # to invoked services. If these values are not set, we create a new tag
    # and a metadata field with basic information about the invoking script.
    #
    if ($ENV{KBRPC_TAG})
    {
	$self->{kbrpc_tag} = $ENV{KBRPC_TAG};
    }
    else
    {
	my ($t, $us) = &$get_time();
	$us = sprintf("%06d", $us);
	my $ts = strftime("%Y-%m-%dT%H:%M:%S.${us}Z", gmtime $t);
	$self->{kbrpc_tag} = "C:$0:$self->{hostname}:$$:$ts";
    }
    push(@{$self->{headers}}, 'Kbrpc-Tag', $self->{kbrpc_tag});

    if ($ENV{KBRPC_METADATA})
    {
	$self->{kbrpc_metadata} = $ENV{KBRPC_METADATA};
	push(@{$self->{headers}}, 'Kbrpc-Metadata', $self->{kbrpc_metadata});
    }

    if ($ENV{KBRPC_ERROR_DEST})
    {
	$self->{kbrpc_error_dest} = $ENV{KBRPC_ERROR_DEST};
	push(@{$self->{headers}}, 'Kbrpc-Errordest', $self->{kbrpc_error_dest});
    }

    #
    # This module requires authentication.
    #
    # We create an auth token, passing through the arguments that we were (hopefully) given.

    {
	my $token = Bio::KBase::AuthToken->new(@args);
	
	if (!$token->error_message)
	{
	    $self->{token} = $token->token;
	    $self->{client}->{token} = $token->token;
	}
        else
        {
	    #
	    # All methods in this module require authentication. In this case, if we
	    # don't have a token, we can't continue.
	    #
	    die "Authentication failed: " . $token->error_message;
	}
    }

    my $ua = $self->{client}->ua;	 
    my $timeout = $ENV{CDMI_TIMEOUT} || (30 * 60);	 
    $ua->timeout($timeout);
    bless $self, $class;
    #    $self->_validate_version();
    return $self;
}




=head2 run_QUAST_app

  $output = $obj->run_QUAST_app($params)

=over 4

=item Parameter and return types

=begin html

<pre>
$params is a kb_quast.QUASTParams
$output is a kb_quast.QUASTAppOutput
QUASTParams is a reference to a hash where the following keys are defined:
	assemblies has a value which is a reference to a list where each element is a kb_quast.assembly_ref
	files has a value which is a reference to a list where each element is a kb_quast.FASTAFile
assembly_ref is a string
FASTAFile is a reference to a hash where the following keys are defined:
	path has a value which is a string
	label has a value which is a string
QUASTAppOutput is a reference to a hash where the following keys are defined:
	report_name has a value which is a string
	report_ref has a value which is a string

</pre>

=end html

=begin text

$params is a kb_quast.QUASTParams
$output is a kb_quast.QUASTAppOutput
QUASTParams is a reference to a hash where the following keys are defined:
	assemblies has a value which is a reference to a list where each element is a kb_quast.assembly_ref
	files has a value which is a reference to a list where each element is a kb_quast.FASTAFile
assembly_ref is a string
FASTAFile is a reference to a hash where the following keys are defined:
	path has a value which is a string
	label has a value which is a string
QUASTAppOutput is a reference to a hash where the following keys are defined:
	report_name has a value which is a string
	report_ref has a value which is a string


=end text

=item Description

Run QUAST and save a KBaseReport with the output.

=back

=cut

 sub run_QUAST_app
{
    my($self, @args) = @_;

# Authentication: required

    if ((my $n = @args) != 1)
    {
	Bio::KBase::Exceptions::ArgumentValidationError->throw(error =>
							       "Invalid argument count for function run_QUAST_app (received $n, expecting 1)");
    }
    {
	my($params) = @args;

	my @_bad_arguments;
        (ref($params) eq 'HASH') or push(@_bad_arguments, "Invalid type for argument 1 \"params\" (value was \"$params\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to run_QUAST_app:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    Bio::KBase::Exceptions::ArgumentValidationError->throw(error => $msg,
								   method_name => 'run_QUAST_app');
	}
    }

    my $url = $self->{url};
    my $result = $self->{client}->call($url, $self->{headers}, {
	    method => "kb_quast.run_QUAST_app",
	    params => \@args,
    });
    if ($result) {
	if ($result->is_error) {
	    Bio::KBase::Exceptions::JSONRPC->throw(error => $result->error_message,
					       code => $result->content->{error}->{code},
					       method_name => 'run_QUAST_app',
					       data => $result->content->{error}->{error} # JSON::RPC::ReturnObject only supports JSONRPC 1.1 or 1.O
					      );
	} else {
	    return wantarray ? @{$result->result} : $result->result->[0];
	}
    } else {
        Bio::KBase::Exceptions::HTTP->throw(error => "Error invoking method run_QUAST_app",
					    status_line => $self->{client}->status_line,
					    method_name => 'run_QUAST_app',
				       );
    }
}
 


=head2 run_QUAST

  $output = $obj->run_QUAST($params)

=over 4

=item Parameter and return types

=begin html

<pre>
$params is a kb_quast.QUASTParams
$output is a kb_quast.QUASTOutput
QUASTParams is a reference to a hash where the following keys are defined:
	assemblies has a value which is a reference to a list where each element is a kb_quast.assembly_ref
	files has a value which is a reference to a list where each element is a kb_quast.FASTAFile
assembly_ref is a string
FASTAFile is a reference to a hash where the following keys are defined:
	path has a value which is a string
	label has a value which is a string
QUASTOutput is a reference to a hash where the following keys are defined:
	shock_id has a value which is a string
	handle has a value which is a kb_quast.Handle
	node_file_name has a value which is a string
	size has a value which is a string
	quast_path has a value which is a string
Handle is a reference to a hash where the following keys are defined:
	hid has a value which is a string
	file_name has a value which is a string
	id has a value which is a string
	url has a value which is a string
	type has a value which is a string
	remote_md5 has a value which is a string

</pre>

=end html

=begin text

$params is a kb_quast.QUASTParams
$output is a kb_quast.QUASTOutput
QUASTParams is a reference to a hash where the following keys are defined:
	assemblies has a value which is a reference to a list where each element is a kb_quast.assembly_ref
	files has a value which is a reference to a list where each element is a kb_quast.FASTAFile
assembly_ref is a string
FASTAFile is a reference to a hash where the following keys are defined:
	path has a value which is a string
	label has a value which is a string
QUASTOutput is a reference to a hash where the following keys are defined:
	shock_id has a value which is a string
	handle has a value which is a kb_quast.Handle
	node_file_name has a value which is a string
	size has a value which is a string
	quast_path has a value which is a string
Handle is a reference to a hash where the following keys are defined:
	hid has a value which is a string
	file_name has a value which is a string
	id has a value which is a string
	url has a value which is a string
	type has a value which is a string
	remote_md5 has a value which is a string


=end text

=item Description

Run QUAST and return a shock node containing the zipped QUAST output.

=back

=cut

 sub run_QUAST
{
    my($self, @args) = @_;

# Authentication: required

    if ((my $n = @args) != 1)
    {
	Bio::KBase::Exceptions::ArgumentValidationError->throw(error =>
							       "Invalid argument count for function run_QUAST (received $n, expecting 1)");
    }
    {
	my($params) = @args;

	my @_bad_arguments;
        (ref($params) eq 'HASH') or push(@_bad_arguments, "Invalid type for argument 1 \"params\" (value was \"$params\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to run_QUAST:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    Bio::KBase::Exceptions::ArgumentValidationError->throw(error => $msg,
								   method_name => 'run_QUAST');
	}
    }

    my $url = $self->{url};
    my $result = $self->{client}->call($url, $self->{headers}, {
	    method => "kb_quast.run_QUAST",
	    params => \@args,
    });
    if ($result) {
	if ($result->is_error) {
	    Bio::KBase::Exceptions::JSONRPC->throw(error => $result->error_message,
					       code => $result->content->{error}->{code},
					       method_name => 'run_QUAST',
					       data => $result->content->{error}->{error} # JSON::RPC::ReturnObject only supports JSONRPC 1.1 or 1.O
					      );
	} else {
	    return wantarray ? @{$result->result} : $result->result->[0];
	}
    } else {
        Bio::KBase::Exceptions::HTTP->throw(error => "Error invoking method run_QUAST",
					    status_line => $self->{client}->status_line,
					    method_name => 'run_QUAST',
				       );
    }
}
 
  
sub status
{
    my($self, @args) = @_;
    if ((my $n = @args) != 0) {
        Bio::KBase::Exceptions::ArgumentValidationError->throw(error =>
                                   "Invalid argument count for function status (received $n, expecting 0)");
    }
    my $url = $self->{url};
    my $result = $self->{client}->call($url, $self->{headers}, {
        method => "kb_quast.status",
        params => \@args,
    });
    if ($result) {
        if ($result->is_error) {
            Bio::KBase::Exceptions::JSONRPC->throw(error => $result->error_message,
                           code => $result->content->{error}->{code},
                           method_name => 'status',
                           data => $result->content->{error}->{error} # JSON::RPC::ReturnObject only supports JSONRPC 1.1 or 1.O
                          );
        } else {
            return wantarray ? @{$result->result} : $result->result->[0];
        }
    } else {
        Bio::KBase::Exceptions::HTTP->throw(error => "Error invoking method status",
                        status_line => $self->{client}->status_line,
                        method_name => 'status',
                       );
    }
}
   

sub version {
    my ($self) = @_;
    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
        method => "kb_quast.version",
        params => [],
    });
    if ($result) {
        if ($result->is_error) {
            Bio::KBase::Exceptions::JSONRPC->throw(
                error => $result->error_message,
                code => $result->content->{code},
                method_name => 'run_QUAST',
            );
        } else {
            return wantarray ? @{$result->result} : $result->result->[0];
        }
    } else {
        Bio::KBase::Exceptions::HTTP->throw(
            error => "Error invoking method run_QUAST",
            status_line => $self->{client}->status_line,
            method_name => 'run_QUAST',
        );
    }
}

sub _validate_version {
    my ($self) = @_;
    my $svr_version = $self->version();
    my $client_version = $VERSION;
    my ($cMajor, $cMinor) = split(/\./, $client_version);
    my ($sMajor, $sMinor) = split(/\./, $svr_version);
    if ($sMajor != $cMajor) {
        Bio::KBase::Exceptions::ClientServerIncompatible->throw(
            error => "Major version numbers differ.",
            server_version => $svr_version,
            client_version => $client_version
        );
    }
    if ($sMinor < $cMinor) {
        Bio::KBase::Exceptions::ClientServerIncompatible->throw(
            error => "Client minor version greater than Server minor version.",
            server_version => $svr_version,
            client_version => $client_version
        );
    }
    if ($sMinor > $cMinor) {
        warn "New client version available for kb_quast::kb_quastClient\n";
    }
    if ($sMajor == 0) {
        warn "kb_quast::kb_quastClient version is $svr_version. API subject to change.\n";
    }
}

=head1 TYPES



=head2 assembly_ref

=over 4



=item Description

An X/Y/Z style reference to a workspace object containing an assembly, either a
KBaseGenomes.ContigSet or KBaseGenomeAnnotations.Assembly.


=item Definition

=begin html

<pre>
a string
</pre>

=end html

=begin text

a string

=end text

=back



=head2 Handle

=over 4



=item Description

A handle for a file stored in Shock.
hid - the id of the handle in the Handle Service that references this shock node
id - the id for the shock node
url - the url of the shock server
type - the type of the handle. This should always be shock.
file_name - the name of the file
remote_md5 - the md5 digest of the file.


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
hid has a value which is a string
file_name has a value which is a string
id has a value which is a string
url has a value which is a string
type has a value which is a string
remote_md5 has a value which is a string

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
hid has a value which is a string
file_name has a value which is a string
id has a value which is a string
url has a value which is a string
type has a value which is a string
remote_md5 has a value which is a string


=end text

=back



=head2 FASTAFile

=over 4



=item Description

A local FASTA file.
path - the path to the FASTA file.
label - the label to use for the file in the QUAST output. If missing, the file name will
be used.


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
path has a value which is a string
label has a value which is a string

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
path has a value which is a string
label has a value which is a string


=end text

=back



=head2 QUASTParams

=over 4



=item Description

Input for running QUAST.
assemblies - the list of assemblies upon which QUAST will be run.
-OR-
files - the list of FASTA files upon which QUAST will be run.


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
assemblies has a value which is a reference to a list where each element is a kb_quast.assembly_ref
files has a value which is a reference to a list where each element is a kb_quast.FASTAFile

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
assemblies has a value which is a reference to a list where each element is a kb_quast.assembly_ref
files has a value which is a reference to a list where each element is a kb_quast.FASTAFile


=end text

=back



=head2 QUASTAppOutput

=over 4



=item Description

Output of the run_quast_app function.
report_name - the name of the KBaseReport.Report workspace object.
report_ref - the workspace reference of the report.


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
report_name has a value which is a string
report_ref has a value which is a string

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
report_name has a value which is a string
report_ref has a value which is a string


=end text

=back



=head2 QUASTOutput

=over 4



=item Description

Ouput of the run_quast function.
shock_id - the id of the shock node where the zipped QUAST output is stored.
handle - the new handle for the shock node.
node_file_name - the name of the file stored in Shock.
size - the size of the file stored in shock.
quast_path - the directory containing the quast output and the zipfile of the directory.


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
shock_id has a value which is a string
handle has a value which is a kb_quast.Handle
node_file_name has a value which is a string
size has a value which is a string
quast_path has a value which is a string

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
shock_id has a value which is a string
handle has a value which is a kb_quast.Handle
node_file_name has a value which is a string
size has a value which is a string
quast_path has a value which is a string


=end text

=back



=cut

package kb_quast::kb_quastClient::RpcClient;
use base 'JSON::RPC::Client';
use POSIX;
use strict;

#
# Override JSON::RPC::Client::call because it doesn't handle error returns properly.
#

sub call {
    my ($self, $uri, $headers, $obj) = @_;
    my $result;


    {
	if ($uri =~ /\?/) {
	    $result = $self->_get($uri);
	}
	else {
	    Carp::croak "not hashref." unless (ref $obj eq 'HASH');
	    $result = $self->_post($uri, $headers, $obj);
	}

    }

    my $service = $obj->{method} =~ /^system\./ if ( $obj );

    $self->status_line($result->status_line);

    if ($result->is_success) {

        return unless($result->content); # notification?

        if ($service) {
            return JSON::RPC::ServiceObject->new($result, $self->json);
        }

        return JSON::RPC::ReturnObject->new($result, $self->json);
    }
    elsif ($result->content_type eq 'application/json')
    {
        return JSON::RPC::ReturnObject->new($result, $self->json);
    }
    else {
        return;
    }
}


sub _post {
    my ($self, $uri, $headers, $obj) = @_;
    my $json = $self->json;

    $obj->{version} ||= $self->{version} || '1.1';

    if ($obj->{version} eq '1.0') {
        delete $obj->{version};
        if (exists $obj->{id}) {
            $self->id($obj->{id}) if ($obj->{id}); # if undef, it is notification.
        }
        else {
            $obj->{id} = $self->id || ($self->id('JSON::RPC::Client'));
        }
    }
    else {
        # $obj->{id} = $self->id if (defined $self->id);
	# Assign a random number to the id if one hasn't been set
	$obj->{id} = (defined $self->id) ? $self->id : substr(rand(),2);
    }

    my $content = $json->encode($obj);

    $self->ua->post(
        $uri,
        Content_Type   => $self->{content_type},
        Content        => $content,
        Accept         => 'application/json',
	@$headers,
	($self->{token} ? (Authorization => $self->{token}) : ()),
    );
}



1;
