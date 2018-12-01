import os

def dedup_help() -> int:
    """
    dedup is a utility to find suspiciously similiar files that 
    may be duplicates. It creates a directory of symbolic links
    that point to the files, and optionally (dangerously) removes
    them.

    All the command line arguments have defaults. To run the program
    with the switches you have supplied, and skip the interrogation
    by the console, use the --quiet option in combination with other
    options, and you just rocket along.

    dedup works by creating a score for each file that indicates the
    likelihood that it is a candidate for removal. The scoring is on
    the half open interval [0 .. 1), where zero indicates that the file
    may not be removed, and values near 1 indicate that if you don't 
    remove it fairly soon, WW III will break out. Most files are somewhere 
    between.

    Files that you cannot remove are given a zero.
    Files are penalized for not having been accesses in a long time.
    Files with the same name as a newer file, are penalized.
    Files with the same name as a newer file, and that have at least
        one common ancestor directory are penalized even more.
    Files are penalized if their contents exactly match another
        file. This is the final step. There is no need to compare every
        file because if two files have different lengths, they 
        are obviously not the same file.
    
    So if you have an ancient file, that is a duplicate of some other
    file, with the same name, somewhere on the same mount point, and it 
    is large and hasn't been accessed in a while, then its score
    may approach 1.0. This program will then produce a list of the worst
    offenders.

    Through the options below, you will have a lot of control over
    how dedup works. You should read through all of them before you
    run the program for the first time. If you have questions you
    can read through this help a second time, or write to the author
    at this address:

        me+dedup@georgeflanagin.com

    THE OPTIONS:
    ==================================================================

    -? / --help  :: This is it; you are here.

    [ --dir {dir-name} [--dir {dir-name} .. ]] 
        This is an optional parameter to name several directories,
        mount points, or drives to include in the search. If --dir
        is present, the --home is only used if it is explicitly
        named.

    --home {dir-name}
        Where you want to start looking, and go down from there. This
        defaults to the user's home directory. 

        [ NOTE: For both --dir and --home, the directory names may
        contain environment variables. They will be correctly
        expanded. -- end note. ]

    --db
        Name of a database file to contain the results, and/or the
        database containing [partial] results from previous runs.

    --follow 
        If present, symbolic links will be dereferenced for purposes
        of consideration of duplicates. Use of this switch requires
        careful consideration, and it is probably only useful in 
        cases where you think you have files in your directory of
        interest that are duplicates of things elsewhere that are
        mentioned by symbolic links that are *also* in your 
        directory of interest.

    --ignore-extensions
        This option is useful with media files where there may be
        .jpg and .JPG and .jpeg files all mixed together. By default,
        --ignore-extensions is *OFF*.

    --ignore-filenames
        This option is useful when searching several mount points or
        directories that may have been created by different people
        at different times. By default, --ignore-filenames is *OFF*

    --links
        If this switch is present, the directory that is associated
        with --output will contain a directory named 'links' that
        will have symbolic links to all the duplicate files. This 
        feature is for convenience in their removal.

    --nice {int} 
        Keep in mind a terabyte of disc could hold one million files 
        at one megabyte each. You should be nice, and frankly, the program
        may run faster in nice mode. The default value is 20, which
        on Linux is as nice as you can be.

    --output {directory-name} 
        This is the directory where names of possibly dup files will 
        be placed. The default is a directory named 'dedups' in the 
        user's home directory. If the directory does not exist, dedup 
        will attempt to create it. This directory is never examined
        for duplicate files, or more correctly, any file in it is 
        assumed to be unique and worth keeping. 

        The output is a CSV file named dedup.YYYY-MM-DD-HH-MM.csv

    --quiet 
        I know what I am doing. Just let me know when you are finished. 
        There is no --verbose option because the program kinda rattles on 
        interminably. By default, --quiet is *OFF*

    --small-file {int} 
        Define the size of a small file in bytes. These will be ignored. 
        Many duplicate small files will indeed clutter the inode space
        in the directory system, but many projects depend on tiny and
        duplicate small .conf files being present. The default value is
        4096.
    """
    print(dedup_help.__doc__)
    return os.EX_OK



