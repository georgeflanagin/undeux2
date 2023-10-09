export undir="$sw/undeux"
export latestpython=$(ls -1 /usr/bin/python3.? | tail -1)

function undeux
{
    command pushd $undir >/dev/null
    $latestpython undeux.py $@
    command popd >/dev/null
}


