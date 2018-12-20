# This can be appended to your .profile or .bashrc

undeux()
{
    if [ "$1" == "install" ]; then
        _undeuxinstaller
        return
    fi

    py=`which python`
    d=`find ~ -name undeux -type d | head -1`    
    "$py $d/undeuxmain.py $@"
}

addhere()
{
    export PYTHONPATH="$PWD:$PYTHONPATH"
}

_undeuxinstaller()
{
    # Is Python installed?
    py=`which python`
    if [ -z $py ]; then
        echo 'You must install the latest Python from python.org'
        return 1
    fi

    # Is Python >= 3.6?
    "$py" - <<END
import sys
if sys.version_info < (3, 7):
    print("You must be on Python 3.6 or later. Please upgrade at python.org")
    sys.exit(1)
END

    # This way, we get the right pip
    minor_version=$?
    if [ $minor_version -eq 0 ]; then 
        return 1
    fi
    alias pip=pip3."$minor_version"
    
    # Make sure we get gkflib
    gkflib=`find ~ -name gkflib -type d | head -1`
    if [ -z $gkflib ]; then
        cd ~
        git clone https://github.com/georgeflanagin/gkflib.git
        cd gkflib
        addhere
    fi        

    # And get undeux
    cd ~
    git clone https://github.com/georgeflanagin/undeux.git
    cd undeux
    addhere

    # Now install the required python packages.
    pip install croniter
    pip install paramiko
    pip install scipy

    echo 'Try running undeux with the "undeux" command. You should see some help.'
}
