script_dir=$(dirname "$(readlink -f "$0")")
echo "script: $0"
echo "script_dir: $script_dir"
export KB_DEPLOYMENT_CONFIG=$script_dir/../deploy.cfg
echo "KB DEPLOY: $KB_DEPLOYMENT_CONFIG"
# Would need input mounting to make this work in JAWS, allowing setting it for now
# WD=/kb/module/work
if [ -f $WD/token ]; then
    cat $WD/token | xargs sh $script_dir/../bin/run_kb_quast_async_job.sh $WD/input.json $WD/output.json
else
    sh $script_dir/../bin/run_kb_quast_async_job.sh $WD/input.json $WD/output.json
    # Another option would be to require the token but set up an auth endpoint, either in the
    # service or nginx, that just returned a fake username and provide a fake token
    # echo "File $WD/token doesn't exist, aborting."
    # exit 1
fi
