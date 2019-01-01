undeux
=======================================================
Table of contents:
1. Summary, method of operation.
2. Operation, the command line switches and what they mean, dependencies, etc.
3. Use cases, how you might use this program.

## Summary

`undeux` is a utility to find suspiciously similiar files that
may be duplicates.

All the command line arguments have defaults. If you run the program
with no arguments, you will be reading the help, just like you are
right now. If you want to accept all the defaults, use the single
argument:

    undeux --just-do-it

### How `undeux` works

undeux works by creating a score for each file that indicates the
likelihood that it is a candidate for removal. The scoring is on
the half open interval `[0 .. 1)`, where zero indicates that the file
may not be removed, and values near 1 indicate that if you don't
remove it fairly soon, WW III will break out somewhere near your
disc drive[s]. Fortunately, most files are somewhere between.

To elaborate:

- Files that you cannot remove are given a zero, and not further
    incorporated into the removal logic. The same is true of a file
    that is too new, or too small.
- Files are penalized for not having been accessed in a long time.
- Files that are large are penalized.
- Files are reported if their contents exactly match another
    file. This is the final step. There is no need to hash every
    file because if two files have different lengths, they
    are obviously not the same file.

So if you have an ancient file, that is a duplicate of some other
file, with the same name, somewhere on the same mount point, and it
is large and hasn't been accessed in a while, then its score
may approach 1.0. This program will then produce a list of the
offenders.

Through the options below, you will have a lot of control over
how undeux works. You should read through all of them before you
run the program for the first time, and as the author I recommend
that you choose just one or two directories to better understand
the effects of your choices. If you have questions you can read
through this help a second time, or write to me at this address:

    `me+undeux@georgeflanagin.com`

## Operation

### Dependencies

This project is built on another of my github projects, namely
[gkflib](git@github.com:georgeflanagin/gkflib.git), and it depends
on a few PyPi libraries that are pip-installable. For the Python noobs
and neolates, this repo has a single file version of the program
that appears to have all the dependencies resolved.

### Command line switches

**NOTE:** All output is written to the combined/joined stderr and
stdout. You can use I/O redirection to write the output to a file.
Example

```bash
python undeux.py --just-do-it 2>myoutput`
```

Creates a file named `myoutput` with the results.

OK, let's continue.

```bash
-? / --help / --explain
```
This is it; you are here. There is no more.

```bash
--big-file {integer}
```
Experimental feature that requires some explanation. On my system I have
this file: 

`-rwxrwxrwx  1 george george 537627361 Jul 22  2016 The.Quartets.PDTV.x264-CBFM.mp4`

It is improbable that another file on my system that is also 537,627,361 bytes
is something else. If you set the value to `--big-file 0` explicitly,
`undeux` goes to paranoid mode. The default value is 256MB, which you may find
a little large for best performance. See use cases for more information.

```bash
--dir {dir-name} [--dir {dir-name} .. ]
```
This is an optional parameter to name several directories,
mount points, or drives to include in the search. If --dir
is not present, the default value is the user's home directory
because this is the most likely target for cleanup.

[[ NOTE: --dir: the directory names may contain environment
variables. They will be correctly expanded. -- end note. ]]

```
--exclude / -x {fragmentary-dir-name} [ -x {fragmentary-dir-name} .. ]
```
Exclude dirs that look like these from consideration. As with the `--dir` 
option, you may name several. This is not a regular expression, just a 
simple fragment to match. 

`--follow-links`
If present, symbolic links will be dereferenced for purposes
of consideration of duplicates. Use of this switch requires
careful consideration, and it is probably only useful in
cases where you think you have files in your directory of
interest that are duplicates of things elsewhere that are
mentioned by symbolic links that are *also* in your
directory of interest.

```bash
--include-hidden
``` 
Undoes the default exclusion of hidden directories. Most 
hidden directories are things like `.git`, where you would
not want to examine a pile of binary files.

```bash
--just-do-it
```
Accept all defaults, and run the program.

```bash
--nice {int}
```
Keep in mind a terabyte of disc could hold one million files
at one megabyte each. You should be nice, and frankly, the program
may run faster in nice mode. The default value is 20, which
on Linux is as nice as you can be.

```bash
--quiet
```
I know what I am doing. Just let me know when you are finished.
This option is normally off, and the program does provide info
as it runs. However, if logorrhea is your thing, then --verbose
is what you want.

```bash
--small-file {int}
```
Define the size of a small file in bytes. These will be ignored.
Many duplicate small files will indeed clutter the inode space
in the directory system, but many projects depend on tiny and
duplicate small .conf files being present. The default value is
4096.

```bash
--verbose
```
Tell all.

```bash
--version
```
Print information about the version of the program and the libraries,
and then exit.

```bash
--young-file {int}
```
Define how new a file needs to be to be ignored from processing.
The idea is that if you downloaded Apocalypse Now from Amazon only
one week ago, then you probably want to keep this whale even
though it is 50+GB. The default is zero (0), i.e., consider all files,
even new ones, when looking for duplicates.

## Use cases

First, you may find it useful to create a bash function to do the 
