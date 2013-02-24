ios-hooker
==========

Python scripts to aid in reverse engineering iOS applications

hooker.py
==========
Automatically parse objective-c header files and produce hooks for class methods, instance methods, and class properties.  Compile generated hooks using Theos (https://github.com/DHowett/theos).

```
mdkir header_files
class-dump-z iOSApp -H -o ./header_files
hooker.py --target ./header_files
```
