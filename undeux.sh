export undir="$PWD"
export latestpython=$(ls /usr/bin/python3.? | tail -1)

function undeux
{
    command pushd $undir
    $latestpython undeux.py
    command popd 
}

