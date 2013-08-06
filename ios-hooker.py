#!/usr/bin/env python

# ===================================================
#                   iOS Hooker
# ===================================================
#
#  About: Hacky Objective-c parser for generating
#  function hooks automagically.  Should work with
#  any current version of Python 2.x or 3.x
#

import os
import re
import sys
import platform
import argparse


if platform.system().lower() in ['linux', 'darwin']:
    INFO = "\033[1m\033[36m[*]\033[0m "
    WARN = "\033[1m\033[31m[!]\033[0m "
else:
    INFO = "[*] "
    WARN = "[!] "

# Makes for easy compiling; this can of course be optionally disabled
KNOWN_TYPES = [
    'id', 'NSObject', 'void', 'char', 'int', 'unsigned', 'double', 'float', 'long', 'bool', 'BOOL',
    'NSAffineTransform','NSAppleEventDescriptor','NSAppleEventManager','NSAppleScript',
    'NSArchiver','NSArray','NSAssertionHandler','NSAttributedString','NSAutoreleasePool',
    'NSBlockOperation','NSBundle','NSCache','NSCachedURLResponse','NSCalendar','NSCharacterSet',
    'NSClassDescription','NSCloneCommand','NSCloseCommand','NSCoder','NSComparisonPredicate',
    'NSCompoundPredicate','NSCondition','NSConditionLock','NSConnection','NSCountCommand',
    'NSCountedSet','NSCreateCommand','NSData','NSDataDetector','NSDate','NSDateComponents',
    'NSDateFormatter','NSDecimalNumber','NSDecimalNumberHandler','NSDeleteCommand','NSDictionary',
    'NSDirectoryEnumerator','NSDistantObject','NSDistantObjectRequest','NSDistributedLock',
    'NSDistributedNotificationCenter','NSEnumerator','NSError','NSException','NSExistsCommand',
    'NSExpression','NSFileCoordinator','NSFileHandle','NSFileManager','NSFileVersion','NSFileWrapper',
    'NSFormatter','NSGarbageCollector','NSGetCommand','NSHashTable','NSHost','NSHTTPCookie',
    'NSHTTPCookieStorage','NSHTTPURLResponse','NSIndexPath','NSIndexSet','NSIndexSpecifier','NSInputStream',
    'NSInvocation','NSInvocationOperation','NSKeyedArchiver','NSKeyedUnarchiver','NSLinguisticTagger',
    'NSLocale','NSLock','NSLogicalTest','NSMachBootstrapServer','NSMachPort','NSMapTable','NSMessagePort',
    'NSMessagePortNameServer','NSMetadataItem','NSMetadataQuery','NSMetadataQueryAttributeValueTuple',
    'NSMetadataQueryResultGroup','NSMethodSignature','NSMiddleSpecifier','NSMoveCommand','NSMutableArray',
    'NSMutableAttributedString','NSMutableCharacterSet','NSMutableData','NSMutableDictionary',
    'NSMutableIndexSet','NSMutableOrderedSet','NSMutableSet','NSMutableString','NSMutableURLRequest',
    'NSNameSpecifier','NSNetService','NSNetServiceBrowser','NSNotification','NSNotificationCenter',
    'NSNotificationQueue','NSNull','NSNumber','NSNumberFormatter','NSObject','NSOperation','NSOperationQueue',
    'NSOrderedSet','NSOrthography','NSOutputStream','NSPipe','NSPointerArray','NSPointerFunctions','NSPort',
    'NSPortCoder','NSPortMessage','NSPortNameServer','NSPositionalSpecifier','NSPredicate','NSProcessInfo',
    'NSPropertyListSerialization','NSPropertySpecifier','NSProtocolChecker','NSProxy','NSQuitCommand',
    'NSRandomSpecifier','NSRangeSpecifier','NSRecursiveLock','NSRegularExpression','NSRelativeSpecifier',
    'NSRunLoop','NSScanner','NSScriptClassDescription','NSScriptCoercionHandler','NSScriptCommand',
    'NSScriptCommandDescription','NSScriptExecutionContext','NSScriptObjectSpecifier','NSScriptSuiteRegistry',
    'NSScriptWhoseTest','NSSet','NSSetCommand','NSSocketPort','NSSocketPortNameServer','NSSortDescriptor',
    'NSSpecifierTest','NSSpellServer','NSStream','NSString','NSTask','NSTextCheckingResult','NSThread',
    'NSTimer','NSTimeZone','NSUbiquitousKeyValueStore','NSUnarchiver','NSUndoManager','NSUniqueIDSpecifier',
    'NSURL','NSURLAuthenticationChallenge','NSURLCache','NSURLConnection','NSURLCredential','NSURLCredentialStorage',
    'NSURLDownload','NSURLHandle','NSURLProtectionSpace','NSURLProtocol','NSURLRequest','NSURLResponse',
    'NSUserAppleScriptTask','NSUserAutomatorTask','NSUserDefaults','NSUserNotification','NSUserNotificationCenter',
    'NSUserScriptTask','NSUserUnixTask','NSUUID','NSValue','NSValueTransformer','NSWhoseSpecifier','NSXMLDocument',
    'NSXMLDTD','NSXMLDTDNode','NSXMLElement','NSXMLNode','NSXMLParser','NSXPCConnection','NSXPCInterface',
    'NSXPCListener','NSXPCListenerEndpoint','NSCoding','NSComparisonMethods','NSConnectionDelegate','NSCopying',
    'NSDecimalNumberBehaviors','NSErrorRecoveryAttempting','NSFastEnumeration','NSFileManagerDelegate',
    'NSFilePresenter','NSKeyedArchiverDelegate','NSKeyedUnarchiverDelegate','NSKeyValueCoding','NSKeyValueObserving',
    'NSLocking','NSMachPortDelegate','NSMetadataQueryDelegate','NSMutableCopying','NSNetServiceBrowserDelegate',
    'NSNetServiceDelegate', 'NSPortDelegate','NSScriptingComparisonMethods','NSScriptKeyValueCoding',
    'NSScriptObjectSpecifiers','NSSecureCoding','NSSpellServerDelegate','NSStreamDelegate',
    'NSURLAuthenticationChallengeSender','NSURLConnectionDataDelegate','NSURLConnectionDelegate',
    'NSURLConnectionDelegate','NSURLHandleClient','NSURLProtocolClient','NSUserNotificationCenterDelegate',
    'NSXMLParserDelegate','NSXPCListenerDelegate','NSXPCProxyCreating',
]
NSLOG = {"int": "d", "unsigned": "d", "BOOL": "d", "float": "g"}


class ObjcType(object):
    ''' Represents an objective-c type '''

    def __init__(self, name, pointer=False):
        self.class_name = name
        self.is_pointer = pointer
        self.comments = ""

    @property
    def is_known(self):
        ''' Returns boolean if the current class is in the NS-STL '''
        # This checks for things like "unsigned int"
        if ' ' in self.class_name:
            return self.class_name.split(' ')[-1] in KNOWN_TYPES
        else:
            return self.class_name in KNOWN_TYPES

    def __str__(self):
        return self.class_name + "*" if self.is_pointer else self.class_name


class ObjcArgument(object):
    ''' Holds values for a method argument '''

    def __init__(self, class_type, component, external_name=""):
        self.external_name = external_name
        self.component = component
        if class_type.endswith('*'):
            self.class_type = ObjcType(class_type[:-1], pointer=True)
        else:
            self.class_type = ObjcType(class_type)

    def __str__(self):
        return "%s:(%s) %s" % (
            self.external_name, str(self.class_type), self.component
        )


class ObjcMethod(object):
    ''' Represents an objective-c function/method '''

    def __init__(self, name, static=False):
        self.method_name = name
        self._arguments = []
        self._ret_type = None
        self.is_static = static

    @property
    def return_type(self):
        ''' Never return None type '''
        return self._ret_type if self._ret_type is not None else ObjcType("void")

    @return_type.setter
    def return_type(self, value):
        ''' Should already be ObjcType() '''
        self._ret_type = value

    @property
    def arguments(self):
        return self._arguments

    @arguments.setter
    def arguments(self, arguments):
        '''
        Objective-c has the dumbest argument syntax of any programming language
        I've ever encountered so parsing it is a little wonky.  This is a dirty
        hack that seems works okay.
        '''
        if 0 < len(arguments):
            args = arguments.split(' ')
            fixed_args = []
            for index, arg in enumerate(args):
                if '(' in arg and ')' in arg:
                    fixed_args.append(arg)
                elif '(' in arg and not ')' in arg:
                    count = 1  # Look forward for closing ')'
                    while ')' not in arg:
                        arg += str(" " + args[index + count])
                        count += 1
                        if len(args) < (index + count):
                            raise ValueError("Invalid syntax; no closing ')'")
                    fixed_args.append(arg)
            for arg in fixed_args:
                ext_name, pair = arg.split(":")
                class_type, component = pair.split(")")
                method_argument = ObjcArgument(
                    class_type[1:],
                    component,
                    external_name=ext_name
                )
                self._arguments.append(method_argument)

    def __str__(self):
        ret = "(%s) " % str(self.return_type)
        ret = "+" + ret if self.is_static else "-" + ret
        return ret + self.method_name + ' '.join(
            [str(arg) for arg in self.arguments]
        )


class ObjcHeader(object):
    ''' Represents an objective-c header file and it's methods, etc '''

    def __init__(self, file_path, unknowns=True, verbose=False):
        self.file_path = os.path.abspath(file_path)
        self.file_name = os.path.basename(self.file_path)
        self.class_fp = open(self.file_path, 'r')
        self.source_code = self.class_fp.read()
        self.verbose = verbose
        self.drop_unknowns = unknowns
        self._class_name = None
        self._hook_count = 0
        self.setters = False
        self.getters = False
        self.params = False
        self.debug = False

    @property
    def class_name(self):
        ''' Get class name from source code '''
        if self._class_name is not None:
            return self._class_name
        else:
            for line in self.source_code.split('\n'):
                if line.startswith('@interface'):
                    class_name = line.split(' ')[1]
                    if self.verbose:
                        print(INFO + "Found class: %s" % class_name)
                    self._class_name = class_name
                    return self._class_name
            raise ValueError("Invalid header syntax, no class name found")

    @property
    def class_methods(self):
        ''' Parse source code and return list of class methods '''
        methods = []
        for line in self.source_code.split('\n'):
            if line.startswith('+'):
                method_name = self.get_method_name(line)
                if self.verbose:
                    print(INFO + "Hooking class method: %s" % method_name)
                ret = self.get_return_type(line)
                if self.drop_unknowns and not ret.is_known:
                    if self.verbose:
                        print(WARN + 'Unknown return type; skipping class method "%s"' % method_name)
                    continue
                args = self.get_arguments(line)
                class_method = ObjcMethod(method_name, static=True)
                class_method.return_type = ret
                class_method.arguments = args
                methods.append(class_method)
        return methods

    @property
    def instance_methods(self):
        ''' Parse source code and return a list of instance methods '''
        methods = []
        for line in self.source_code.split('\n'):
            if line.startswith('-'):
                method_name = self.get_method_name(line)
                if method_name == '.cxx_destruct' or method_name == 'cxx_construct':
                    continue
                if self.verbose:
                    print(INFO + "Hooking instance method: %s" % method_name)
                ret = self.get_return_type(line)
                if self.drop_unknowns and not ret.is_known:
                    if self.verbose:
                        print(WARN + 'Unknown return type; skipping instance method "%s"' % method_name)
                    continue
                else:
                    args = self.get_arguments(line)
                    instance_method = ObjcMethod(method_name)
                    instance_method.return_type = ret
                    instance_method.arguments = args
                    methods.append(instance_method)
        return methods

    @property
    def properties(self):
        ''' Parse source code and return list of class properties '''
        _properties = []
        for line in self.source_code.split('\n'):
            if line.startswith("@property"):
                name = self.get_property_name(line)
                property_type = self.get_property_type(line)
                if self.drop_unknowns and not property_type.is_known:
                    if self.verbose:
                        print(WARN + 'Unknown return type "%s", skipping property "%s"' % (
                            (property_type.class_name, name,)
                        ))
                    continue
                else:
                    class_property = ObjcMethod(name)
                    class_property.return_type = property_type
                    _properties.append(class_property)
        return _properties

    def get_method_name(self, line):
        ''' Get method name from a line of source '''
        line = line[line.index(")") + 1:]
        end = line.index(":") if ':' in line else -1
        return line[:end]

    def get_return_type(self, line):
        ''' Get the return value from a line of source '''
        ctype = line[2:line.index(')') + 1]
        pointer = '*' in ctype
        return ObjcType(ctype[:-1], pointer=pointer)

    def get_arguments(self, line):
        ''' Get function arguments from a line of source '''
        return line[line.index(":"):-1] if ':' in line else ""

    def get_property_name(self, line):
        ''' Get a property's name from a line of source '''
        return line.split(" ")[-1][:-1]

    def get_property_type(self, line):
        ''' Get property type from line of source '''
        name = line[line.index(")") + 1:line.rindex(" ")]
        ptr = name.endswith("*")
        if ptr:  # Cut off "*"
            name = name[:-1]
        if name.startswith(" "):
            return ObjcType(name[1:], pointer=ptr)  
        else:
            return ObjcType(name, pointer=ptr)

    def filter_methods(self, methods, regex):
        '''
        Filter methods based on matching method name  to regular expression
        '''
        return [func for func in methods if regex.match(func.method_name)]

    def save_hooks(self, output_fp, regex=None):
        ''' Parse an entire class header file '''
        if self.class_name is not None:
            try:
                if regex is not None:
                    self.__regex__(output_fp, regex)
                else:
                    self.__save__(output_fp,
                        self.properties,
                        self.class_methods,
                        self.instance_methods
                    )
            except IOError:
                if not self.verbose:
                    sys.stdout.write('\n')
                print(WARN + "Error while writing hooks for %s" % self.class_name)
            except Exception as error:
                if self.verbose:
                    sys.stdout.write(WARN + str(error) + '\n')
                else:
                    print(WARN + "Error while parsing file.")

    def __regex__(self, output_fp, regex):
        ''' Created hooks based on methods that match a regular expression '''
        regex = compile_regex(regex)
        properties = self.filter_methods(self.properties, regex)
        class_methods = self.filter_methods(self.class_methods, regex)
        instance_methods = self.filter_methods(self.instance_methods, regex)
        if 0 < len(properties) + len(class_methods) + len(instance_methods):
            self.__save__(output_fp, properties, class_methods, instance_methods)

    def __save__(self, output_fp, properties, class_methods, instance_methods):
        ''' Save hooks to output file '''
        self.write_header(output_fp)
        output_fp.write("%"+"hook %s\n\n" % self.class_name)
        if self.getters or self.setters:
            self.write_methods(output_fp, properties, etters=True, comment="Properties")
        self.write_methods(output_fp, class_methods, comment="Class Methods")
        self.write_methods(output_fp, instance_methods, comment="Instance Methods")
        output_fp.write("%"+"end\n\n\n")

    def write_header(self, output_fp):
        ''' Write comment header to output file '''
        output_fp.write("/*==%s\n" % str("=" * len(self.class_name)))
        output_fp.write("  %s  \n" % self.class_name)
        output_fp.write(str("=" * len(self.class_name)) + "==*/\n\n")

    def write_methods(self, output_fp, methods, etters=False, comment=None):
        ''' Write hooks for a list of methods to output file '''
        if 0 < len(methods):
            if comment is not None:
                output_fp.write("/* %s */\n" % comment)
            for method in methods:
                if etters:
                    self.write_etters(output_fp, method)
                else:
                    self._hook_count += 1
                    output_fp.write("%s {\n" % str(method))
                    output_fp.write("    %" + "log;\n")
                    if self.params:
                        self.write_params(output_fp, method.arguments)
                    if 'void' in str(method.return_type):
                        output_fp.write("    %" + "orig;\n")
                    else:
                        output_fp.write("    return %" + "orig;\n")
                    output_fp.write("}\n\n")
            output_fp.write("\n")
            
    def write_params(self, output_fp, arguments):
        for arg in arguments:
            output_fp.write('    NSLog(@"    [Param]%s -> ' % str(arg))
            printf = "@" if str(arg.class_type) not in NSLOG else NSLOG[str(arg.class_type)]
            output_fp.write('%' + printf + '", %s);\n' % arg.component)

    def write_etters(self, output_fp, method):
        '''
        Here we deal with objective-c's dumbass getter/setter methods.
        They may not show up in the class dump but they're magically 
        there.  Use this for @property's
        ''' 
        property_name = method.method_name
        etter_name = "et" + property_name[0].upper() + property_name[1:]
        if self.getters:
            self._hook_count += 1
            output_fp.write("-(%s) " % method.return_type)
            output_fp.write("g%s {\n" % etter_name)
            if self.debug:
                output_fp.write('    NSLog(@" >>> Enter %s Getter >>>");\n' % property_name)
            output_fp.write("    %s %s = " % (method.return_type, property_name))
            output_fp.write("%" + "orig;\n")
            output_fp.write('    NSLog(@"[<- Getter](%s) %s: ' % (str(method.return_type), property_name))
            printf = "@" if str(method.return_type) not in NSLOG else NSLOG[str(method.return_type)]
            output_fp.write('%'+'%s", %s);\n' % (printf, property_name))
            output_fp.write('    return %s;\n' % property_name)
            output_fp.write("}\n")
        if self.setters:
            self._hook_count += 1
            output_fp.write("-(void) s"+etter_name+": ")
            output_fp.write("(%s)%s {\n" % (method.return_type, property_name))
            if self.debug:
                output_fp.write('    NSLog(@" >>> Enter %s Setter >>>");\n' % property_name)
            output_fp.write('    NSLog(@"[Setter ->](%s) %s: ' % (str(method.return_type), property_name))
            printf = "@" if str(method.return_type) not in NSLOG else NSLOG[str(method.return_type)]
            output_fp.write('%'+'%s", %s);\n' % (printf, property_name))
            output_fp.write('    %'+'orig(%s);\n' % property_name)
            output_fp.write('}\n')
        output_fp.write('\n')


### Functions
def display_info(msg):
    ''' Clearline and print message '''
    sys.stdout.write(chr(27) + '[2K')
    sys.stdout.write('\r' + INFO + msg)
    sys.stdout.flush()

def compile_regex(expression):
    ''' Ensures we got a valid regex from user '''
    try:
        return re.compile(expression)
    except:
        print(WARN + "Invalid regular expression")
        os._exit(1)

def write_includes(output_fp):
    ''' Add basic includes to the tweak '''
    output_fp.write('#import <CoreFoundation/CoreFoundation.h>\n')
    output_fp.write('#import <Foundation/Foundation.h>\n')
    output_fp.write('#import <Security/Security.h>\n')
    output_fp.write('#import <Security/SecCertificate.h>\n')
    output_fp.write('\n')
    output_fp.write('#import "substrate.h"\n')
    output_fp.write('\n\n')

def write_load_hook(output_fp):
    ''' Log on Dylib load '''
    output_fp.write("/* Dylib Constructor */\n")
    output_fp.write("%"+"ctor {\n")
    output_fp.write('    NSLog(@" --- iOS Hooker Loaded: %ss --- ", __FILE__);\n' % "%")
    output_fp.write("}\n\n")

def parser_headers(ls, output_fp, args):
    ''' Parse list of header files '''
    errors = 0
    total_hooks = 0
    for index, header_file in enumerate(ls):
        display_info("Parsing %d of %d files: %s... " % (
            index + 1, len(ls), header_file[:-2],
        ))
        if args.verbose:
            sys.stdout.write('\n')
        try:
            objc = ObjcHeader(header_file, args.unknowns, args.verbose)
            objc.setters = args.setters
            objc.getters = args.getters
            objc.params = args.params
            objc.debug = args.debug
            objc.save_hooks(output_fp, args.method_regex)
            total_hooks += objc._hook_count
        except ValueError as error:
            errors += 1
            if args.verbose:
                print(WARN + "Error: Invalid objective-c header file; %s" % error)
    display_info("Successfully parsed %d of %d file(s)\n" % (
        len(ls) - errors, len(ls),
    ))
    print(INFO + "Generated %d function hook(s)" % total_hooks)

def scan_directory(class_dir, args):
    ''' Scan directory and parse header files '''
    path = os.path.abspath(class_dir)
    ls = filter(lambda file_name: file_name.endswith('.h'), os.listdir(path))
    if not args.next_step:
        ls = filter(lambda file_name: not file_name[:-2] in KNOWN_TYPES, ls)
    if args.file_regex is not None:
        regular_expression = compile_regex(args.file_regex)
        ls = filter(regular_expression.match, ls)
    print(INFO + "Found %s target file(s) in target directory" % len(ls))
    return ls


### Main
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate hooks for an objc class header file',
    )
    parser.add_argument('--version',
        action='version',
        version='%(prog)s v0.1.1'
    )
    parser.add_argument('--verbose', '-v',
        help='display verbose output (default: false)',
        action='store_true',
        dest='verbose',
    )
    parser.add_argument('--target', '-t',
        help='file or directory with objc header file(s)',
        dest='target',
        nargs='*',
        required=True,
    )
    parser.add_argument('--output', '-o',
        help='output file with hooks (default: Tweak.xm)',
        default='Tweak.xm',
    )
    parser.add_argument('--append', '-a',
        help='append output file (default: false)',
        action='store_true',
        dest='append',
    )
    parser.add_argument('--next-step', '-n',
        help='parse and hook NS class files (default: false)',
        action='store_true',
        dest='next_step',
    )
    parser.add_argument('--includes', '-i',
        help='add basic #include files to tweak (default: false)',
        dest='includes',
        action='store_true',
    )
    parser.add_argument('--load-hook', '-l',
        help='generate hook when dylib is loaded (default: false)',
        action='store_true',
        dest='load_hook',
    )
    parser.add_argument('--unknown-types', '-u',
        help='create hooks for functions with unknown return types (may cause compiler errors)',
        action='store_false',
        dest='unknowns',
    )
    parser.add_argument('--file-regex', '-f',
        help='only hook classes with file names that match a given regex (only valid with directory)',
        dest='file_regex',
        default=None,
    )
    parser.add_argument('--method-regex', '-m',
        help='only create hooks for methods that match a given regex',
        dest='method_regex',
        default=None,
    )
    parser.add_argument('--getters', '-g',
        help='create hooks for @property getters (default: false)',
        dest='getters',
        action='store_true',
    )
    parser.add_argument('--setters', '-s',
        help='create hooks for @property setters (default: false)',
        dest='setters',
        action='store_true',
    )
    parser.add_argument('--params', '-p',
        help='log function parameter values (default: false)',
        dest='params',
        action='store_true',
    )
    parser.add_argument('--debug',
        help='create debug logging messages for getters/setters (default: false)',
        dest='debug',
        action='store_true',
    )
    args = parser.parse_args()
    mode = 'a+' if args.append else 'w+'
    output_fp = open(args.output, mode)
    if args.includes:
        if args.verbose:
            print(INFO + "Adding basic #includes to tweak file")
        write_includes(output_fp)
    if args.load_hook:
        if args.verbose:
            print(INFO + "Adding load hook to tweak file")
        write_load_hook(output_fp)
    if 1 == len(args.target) and os.path.isdir(args.target[0]):
        args.target = scan_directory(args.target[0], args)
    else:
        args.target = filter(lambda file_name: os.path.exists(file_name), args.target)
    if 0 < len(args.target):
        parser_headers(args.target, output_fp, args)
        output_fp.seek(0)
        length = len(output_fp.read())
        output_fp.close()
        print(INFO + "Hooks written to: "),
        print(args.output + " (%d bytes)" % length)
    else:
        print(WARN + "No valid targets found")
