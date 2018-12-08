`undeux` is a utility to find suspiciously similiar files that 
may be duplicates. It creates a directory of symbolic links
that point to the suspect files, and optionally (and dangerously) 
removes them.

All the command line arguments have defaults. If you run the program
with no arguments, you will be reading this help, just like you are
right now. If you want to accept all the defaults, use the single
argument:

undeux --just-do-it

undeux works by creating a score for each file that indicates the
likelihood that it is a candidate for removal. The scoring is on
the half open interval [0 .. 1), where zero indicates that the file
may not be removed, and values near 1 indicate that if you don't 
remove it fairly soon, WW III will break out somewhere near your
disc drive[s]. Most files are somewhere between.

To elaborate:

- Files that you cannot remove are given a zero, and not further
incorporated into the removal logic.
- Files are penalized for not having been accesses in a long time.
- Files with the same name as a newer file, are penalized.
- Files with the same name as a newer file, and that have at least
one common ancestor directory are penalized even more.
- Files are penalized if their contents exactly match another
file. This is the final step. There is no need to compare every
file because if two files have different lengths, they 
are obviously not the same file.

Users of LaTeX may note that this is the same logic used to determine
page breaks, namely that all page breaks are ugly, and we choose
the least ugly according to the rules. 

So if you have an ancient file, that is a duplicate of some other
file, with the same name, somewhere on the same mount point, and it 
is large and hasn't been accessed in a while, then its score
may approach 1.0. This program will then produce a list of the worst
offenders.

Through the options below, you will have a lot of control over
how undeux works. You should read through all of them before you
run the program for the first time, and as the author I recommend
that you choose just one or two directories to better understand
the effects of your choices. If you have questions you can read 
through this help a second time, or write to me at this address:

me+undeux@georgeflanagin.com

THE OPTIONS:
==================================================================

-? / --help / --explain :: This is it; you are here. There is no
more.

--db
Name of a database file to contain the results, and/or the
database containing [partial] results from previous runs. By
default, the database is created as undeux.db in the directory
named by the --output switch.

At the conclusion of the run, the database is optionally 
exported to a CSV file named undeux.YYYY-MM-DD-HH-MM.csv 
or a file named undeux.YYYY-MM-DD-HH-MM.msgpack depending
on the value of --export.     

--dir {dir-name} [--dir {dir-name} .. ]
This is an optional parameter to name several directories,
mount points, or drives to include in the search. If --dir
is not present, the default value is the user's home.

[[ NOTE: --dir: the directory names may contain environment 
variables. They will be correctly expanded. -- end note. ]]

--exclude / -x {dir-name} [ -x {dir-name} .. ]
Exclude these dirs from consideration. This is done primarly
for excluding things like `.git` directories, where there 
are certainly no files that should be removed.        

--export {csv | [msg]pack }
By default, this switch is *OFF*. If you would like to export
the contents of the database then a file will be created
as described in the --db switch above.

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
`.jpg` and `.JPG` and `.jpeg` files all mixed together. By 
default, --ignore-extensions is *OFF*. If this switch is
engaged, then x.jpg, x.JPG, and x.JpEg will all be considered
to be the same file name, possibly interfering with each 
other.

--just-do-it
Accept all defaults, and run the program.  

--link-dir
If this switch is present, the directory that is associated
with `--output` will contain a directory named 'links' that
will have symbolic links to all the duplicate files. This 
feature is for convenience in their removal.

--nice {int} 
Keep in mind a terabyte of disc could hold one million files 
at one megabyte each. You should be nice, and frankly, the program
may run faster in nice mode. The default value is 20, which
on Linux is as nice as you can be.

--output {directory-name} 
This is the directory where names of possibly dup files will 
be placed. The default is a directory named 'undeuxs' in the 
user's home directory, so `~/undeuxs` on Linux and UNIX, and
`C:\undeuxs` on Windows. If the directory does not exist, undeux 
will attempt to create it. 

This directory is *never* examined for duplicate files, or more 
correctly, any file in it is assumed to be unique and worth keeping. 

--quiet 
I know what I am doing. Just let me know when you are finished. 
This option is normally off, and the program does provide info
as it runs. However, if logorrhea is your thing, then --verbose
is what you want.

--small-file {int} 
Define the size of a small file in bytes. These will be ignored. 
Many duplicate small files will indeed clutter the inode space
in the directory system, but many projects depend on tiny and
duplicate small .conf files being present. The default value is
4096.

--verbose
Tell all.

--version
Print information about the version of the program and the libraries,
and then exit.

--young-file {int} 
Define how new a file needs to be to be ignored from processing.
The idea is that if you downloaded Apocalypse Now from Amazon only
one week ago, then you probably want to keep this whale even 
though it is 50+GB. 


