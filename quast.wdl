version 1.0

workflow sdk_quast_test {
  input {
    Array[File] files
  }

  call quast {
    input:
      files = files
  }
}

task quast {
  input {
    Array[File] files
    Int total = length(files)
  }

  command <<<
    # No module callbacks
    export SDK_CALLBACK_URL="http://fakeendpointthatdoesntexist.com"

    # Not calling any services so no config file needed
    export KBASE_ENDPOINT="http://fakeendpointthatdoesntexist.com"

    # Hack to allow the code to run scripts, mounting output could fix this
    cp -R /kb/module/scripts scripts
    cp -R /kb/module/bin bin
    cp -R /kb/module/lib lib
    cp /kb/module/deploy.cfg deploy.cfg
    
    # Hack to make the code not write in /kb/module/work, mounting output
    # to work would work here
    mkdir work
    export WD=$(pwd)
    echo "WD=$WD"
    
    # make a directory for output. Ideally we'd mount this to /kb/module/work
    mkdir __output__

    # This is an insane hack to make the quast input JSON. It's as minimal
    # as possible here, but this isn't workable in general - we need
    # input/output mounting so we can predict the file paths and create
    # the JSON serverside at submit time
    FILE=~{files[0]}
    FILENAME=$(basename $FILE)
    echo "{" > input.json
    echo "  \"method\": \"kb_quast.run_QUAST_local\"," >> input.json
    echo "  \"params\": [" >> input.json
    echo "    {" >> input.json
    echo "      \"files\": [" >> input.json
    echo -n "        {\"path\": \"$FILE\", \"label\": \"$FILENAME\"}" >> input.json

    FILES=('~{sep="' '" files}')
    for (( c = 1; c < ~{total}; c++ )); do
        FILE=${FILES[$c]}
        FILENAME=$(basename $FILE)
        echo , >> input.json
        echo -n "        {\"path\": \"$FILE\", \"label\": \"$FILENAME\"}" >> input.json
    done
   
    echo "" >> input.json
    echo "      ]," >> input.json
    echo "      \"quast_path\": \"$(pwd)/__output__\"" >> input.json
    echo "    }" >> input.json
    echo "  ]" >> input.json
    echo "}" >> input.json

    # hack to use the copied scripts dir rather than the linked one.
    # if work can be mounted as writeable to output I think this isn't needed
    ./scripts/entrypoint.sh async
    EC=$?

    echo "Entrypoint exit code: $EC"

    find __output__ -type f > ./output_files.txt

    if [ $EC -ne 0 ]; then
        exit $EC
    fi
  >>>

  output {
    Array[File] output_files = read_lines("output_files.txt")
    File stdout = "stdout"
    File stderr = "stderr"
  }

  runtime {
    docker: "ghcr.io/kbaseapps/kb_quast:pr-36@sha256:5bb0d1bcf15de1fbf8596d3c4351ff6610a85ec1a0676fc18b224294c505edd0"
    runtime_minutes: 20
    memory: "100 GB"
    cpu: 4
  }
}
