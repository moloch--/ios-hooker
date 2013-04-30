ios-hooker
==========

This a Python script to aid in reverse engineering iOS applications.  It's a hacky Objc header parser, and can automatically generate function hooks based on class dumps.  For best results use [class-dump-z](https://code.google.com/p/networkpx/wiki/class_dump_z)

hooker.py
==========
Automatically parse objective-c header files and produce hooks for class methods, instance methods, and class properties.  Compile generated hooks using [Theos](https://github.com/DHowett/theos)

```
mkdir header_files
class-dump-z iOSApp -H -o ./header_files
hooker.py --target ./header_files
```

or target a single class file:
```
hooker.py --target FooHeader.h
```


Usage
==============
```
usage: hooker.py [-h] [--version] [--verbose] --target TARGET
                 [--output OUTPUT] [--append] [--next-step] [--load-hook]
                 [--unknown-types] [--prefix PREFIX] [--file-regex FILE_REGEX]
                 [--method-regex METHOD_REGEX] [--getters] [--setters]

Generate hooks for an objc class header file

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --verbose, -v         display verbose output (default: false)
  --target TARGET, -t TARGET
                        file or directory with objc header file(s)
  --output OUTPUT, -o OUTPUT
                        output file with hooks (default: Tweak.xm)
  --append, -a          append output file (default: false)
  --next-step, -n       parse and hook NS class files (default: false)
  --load-hook, -l       generate hook when dylib is loaded (default: false)
  --unknown-types, -u   create hooks for functions with unknown return types
                        (may cause compiler errors)
  --prefix PREFIX, -p PREFIX
                        only hook classes with a given file name prefix (only
                        valid with directory)
  --file-regex FILE_REGEX, -f FILE_REGEX
                        only hook classes with file names that match a given
                        regex (only valid with directory)
  --method-regex METHOD_REGEX, -m METHOD_REGEX
                        only create hooks for methods that match a given regex
  --getters, -g         create hooks for @property getters (default: false)
  --setters, -s         create hooks for @property setters (default: false)
```
