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
    # Not calling any services so no config file needed
    export KBASE_ENDPOINT="http://fakeendpointthatdoesntexist.com"
    
    # Hack to make the code not write in /kb/module/work, mounting output to work would work here
    mkdir work
    export WD=$(pwd)
    echo "WD=$WD"
    
    # make a directory for output. Ideally we'd mount this to /kb/module/work
    mkdir __output__

    # This is an insane hack to make the quast input JSON. It's as minimal as possible here,
    # but this isn't workable in general - we need input/output mounting so we can predict the file
    # paths and create the JSON serverside at submit time
    export quote="\""
    echo "quote=$quote"
    export file1=~{files[0]}
    export file1name=$(basename file1)

    echo "{\"files\": [" > input.json
    echo -n "    {\"path\": \"$file1\"," >> input.json
    echo -n " \"label\": \"" >> input.json
    echo -n $file1name >> input.json
    echo -n $quote} >> input.json

    FILES=('~{sep="' '" files}')
    for (( c = 1; c < ~{total}; c++ )); do
        FILE=$FILES[$c]
        FILENAME=$(basename $FILE)
        echo , >> input.json
        echo -n "    {"\path\": \"$FILE\", \"label\": \"$FILENAME\"}">>input.json
    done
        
    echo "\n  ],\n \"quast_path\": \"$(pwd)/__output__\"">>input.json
    echo "}">>input.json

    /kb/module/scripts/entrypoint.sh async
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
    docker: "ghcr.io/kbaseapps/kb_quast:pr-36"
    runtime_minutes: 20
    memory: "100 GB"
    cpu: 4
  }
}