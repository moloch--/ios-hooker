#!/usr/bin/env python

# ===================================================
#                   iOS Hooker
# ===================================================
#
#  About: Hacky Objective-c parser for generating 
#  function hooks automagically.
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

KNOWN_TYPES = [
    'id', 'NSObject', 'void', 'char', 'int', 'unsigned', 'double', 'float', 'long', 'BOOL',
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
    'NSNetServiceDelegate','NSObject','NSPortDelegate','NSScriptingComparisonMethods','NSScriptKeyValueCoding',
    'NSScriptObjectSpecifiers','NSSecureCoding','NSSpellServerDelegate','NSStreamDelegate',
    'NSURLAuthenticationChallengeSender','NSURLConnectionDataDelegate','NSURLConnectionDelegate',
    'NSURLConnectionDelegate','NSURLHandleClient','NSURLProtocolClient','NSUserNotificationCenterDelegate',
    'NSXMLParserDelegate','NSXPCListenerDelegate','NSXPCProxyCreating',
]


class ObjcType(object):
    
    def __init__(self, name, pointer=False):
        self.class_name = name
        self.is_pointer = pointer
    
    def is_known(self):
        if ' ' in self.class_name:
            return self.class_name.split(' ')[-1] in KNOWN_TYPES
        else:
            return self.class_name in KNOWN_TYPES
    
    def __str__(self):
        return self.class_name+"*" if self.is_pointer else self.class_name


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
    
    def __init__(self, name, static=False):
        self.method_name = name
        self._arguments = []
        self._return_type = None
        self.is_static = static

    @property
    def return_type(self):
        ''' Never return None type '''
        if self._return_type is None:
            return ObjcType("void")
        else:
            return self._return_type

    @return_type.setter
    def return_type(self, value):
        ''' Should already be ObjcType() '''
        self._return_type = value

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
                            raise ValueError("Invalid arg syntax; no closing ')'")
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
        name = "(%s) " % str(self.return_type)
        name = "+"+name if self.is_static else "-"+name
        return name + self.method_name + ' '.join([str(arg) for arg in self.arguments])


class ObjcHeader(object):
    
    def __init__(self, file_path, unknowns=True, verbose=False):
        self.file_path = os.path.abspath(file_path)
        self.file_name = os.path.basename(self.file_path)
        self.class_fp = open(self.file_path, 'r')
        self.source_code = self.class_fp.read()
        self.verbose = verbose
        self.drop_unknowns = unknowns
        self._class_name = None
        self._hook_count = 0
    
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
                        sys.stdout.write(INFO + "Found class: %s\n" % class_name)
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
                if self.drop_unknowns and not ret.is_known():
                    if self.verbose:
                        print(WARN+'Unknown return type; skipping class method %s' % method_name)
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
                if method_name == '.cxx_destruct':
                    continue
                if self.verbose:
                    print(INFO+"Hooking instance method: %s" % method_name)
                ret = self.get_return_type(line)
                if self.drop_unknowns and not ret.is_known():
                    if self.verbose:
                        print(WARN+'Unknown return type; skipping instance method %s' % method_name)
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
                if self.drop_unknowns and not property_type.is_known():
                    if self.verbose:
                        print(WARN+'Unknown return type; skipping property %s' % name)
                    continue
                else:
                    class_property = ObjcMethod(name)
                    class_property.return_type = property_type
                    _properties.append(class_property)
        return _properties

    def get_method_name(self, line):
        ''' Get method name from a line of source '''
        start = line.index(')')
        if ':' in line:
            end = line.index(":")
        else:
            end = -1
        return line[start + 1:end]
    
    def get_return_type(self, line):
        ''' Get the return value from a line of source '''
        ctype = line[:line.index(')') + 1]
        pointer = '*' in ctype
        return ObjcType(ctype[2:-1], pointer=pointer)
    
    def get_arguments(self, line):
        ''' Get function arguments from a line of source '''
        return line[line.index(":"):-1] if ':' in line else ""
    
    def get_property_name(self, line):
        ''' Get a property's name from a line of source '''
        return line.split(" ")[-1][:-1]
    
    def get_property_type(self, line):
        ''' Get property type from line of source '''
        start = line.index(")")
        return ObjcType(line[start + 1:].split(" ")[1])

    def filter_methods(self, methods, regex):
        ''' Filter methods based on regular expression '''
        ls = []
        for method in methods:
            if regex.match(method.method_name):
                ls.append(method)
        return ls

    def save_hooks(self, output_fp, regex=None):
        ''' Parse an entire class header file '''
        if self.class_name is not None:
            try:
                if regex is not None:
                    self.__regex__(output_fp, regex)
                else:
                    self.__save__(output_fp, 
                        self.properties, self.class_methods, self.instance_methods
                    )
            except:
                if not self.verbose: sys.stdout.write('\n')
                print(WARN+"Error while writing hooks for %s" % self.class_name)   
        elif verbose:
            print(WARN+"No objective-c class in %s" % class_fp.name)

    def __regex__(self, output_fp, regex):
        ''' Created hooks based on regular expression '''
        regex = compile_regex(regex)
        properties = self.filter_methods(self.properties, regex)
        class_methods = self.filter_methods(self.class_methods, regex)
        instance_methods = self.filter_methods(self.instance_methods, regex)
        if 0 < len(properties) + len(class_methods) + len(instance_methods):
            self.__save__(output_fp, properties, class_methods, instance_methods)            

    def __save__(self, output_fp, properties, class_methods, instance_methods):
        self.write_header(output_fp)
        output_fp.write("%"+"hook %s\n\n" % self.class_name)
        self.write_methods(output_fp, properties, "Properties")
        self.write_methods(output_fp, class_methods, "Class Methods")
        self.write_methods(output_fp, instance_methods, "Instance Methods")
        output_fp.write("%"+"end\n\n\n")

    def write_header(self, output_fp):
        ''' Write comment header to output file '''
        output_fp.write("/*==%s\n" % str("=" * len(self.class_name)))
        output_fp.write("  %s  \n" % self.class_name)
        output_fp.write(str("=" * len(self.class_name)) + "==*/\n\n")
    
    def write_methods(self, output_fp, methods, comment=None):
        ''' Write hooks for a list of methods to output file '''
        if 0 < len(methods):
            if comment is not None:
                output_fp.write("/* %s */\n" % comment)
            for method in methods:
                self._hook_count += 1
                output_fp.write("%s {\n" % str(method))
                output_fp.write("    %"+"log;\n")
                if 'void' in str(method.return_type):
                    output_fp.write("    %"+"orig;\n")
                else:
                    output_fp.write("    return %"+"orig;\n")
                output_fp.write("}\n")
            output_fp.write("\n")

def display_info(msg):
    sys.stdout.write(chr(27) + '[2K')
    sys.stdout.write('\r' + INFO + msg)
    sys.stdout.flush()

def compile_regex(expression):
    try:
        return re.compile(expression)
    except:
        print(WARN+"Invalid regular expression")
        os._exit(1)

def scan_directory(class_dir, prefix, output_fp, next_step, 
    unknowns, file_regex, method_regex, verbose):
    ''' Scan directory and parse header files '''
    path = os.path.abspath(class_dir)
    ls = filter(lambda file_name: file_name.endswith('.h'), os.listdir(path))
    if prefix is not None:
        ls = filter(lambda file_name: file_name.startswith(prefix), ls)
    if not next_step:
        ls = filter(lambda file_name: not file_name.startswith('NS'), ls)
    if file_regex is not None:
        regular_expression = compile_regex(file_regex)
        ls = filter(regular_expression.match, ls)
    print(INFO + "Found %s file(s) in target directory" % len(ls))
    errors = 0
    total_hooks = 0
    for index, header_file in enumerate(ls):
        display_info("Parsing %d of %d files: %s... " % (
            index + 1, len(ls), header_file[:-2],
        ))
        if verbose: sys.stdout.write('\n')
        try:
            objc = ObjcHeader(path + '/' + header_file, unknowns, verbose)
            objc.save_hooks(output_fp, method_regex)
            total_hooks += objc._hook_count
        except ValueError:
            errors += 1
            if verbose:
                print(WARN+"Error: Invalid objective-c header file")
    display_info("Successfully parsed %d of %d file(s)\n" % (
        len(ls) - errors, len(ls),
    ))
    print(INFO+"Generated %d function hooks" % total_hooks)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate hooks for an objc class header file',
    )
    parser.add_argument('--version', 
        action='version', 
        version='%(prog)s v0.1'
    )
    parser.add_argument('--target', '-t',
        help='file or directory with objc header file(s)',
        dest='target',
        required=True,
    )
    parser.add_argument('--output', '-o',
        help='output file with hooks (default: Tweak.xm)',
        default='Tweak.xm',
    )
    parser.add_argument('--next-step', '-n',
        help='parse and hook NS class files (default: false)',
        action='store_true',
        dest='next_step',
    )
    parser.add_argument('--verbose', '-v',
        help='display verbose output (default: false)',
        action='store_true',
        dest='verbose',
    )
    parser.add_argument('--append', '-a',
        help='append output file (default: false)',
        action='store_true',
        dest='append',
    )
    parser.add_argument('--prefix', '-p',
        help='only hook classes with a given file name prefix (only valid with directory)',
        dest='prefix',
        default=None,
    )
    parser.add_argument('--unknown-types', '-u',
        help='create hooks for functions with unknown return types (may cause compiler errors)',
        action='store_false',
        dest='unknowns',
    )
    parser.add_argument('--file-regex', '-fr',
        help='only hook classes with file names that match a given regex (only valid with directory)',
        dest='file_regex',
        default=None,
    )
    parser.add_argument('--method-regex', '-mr',
        help='only create hooks for methods that match a given regex',
        dest='method_regex',
        default=None,
    )
    args = parser.parse_args()
    if os.path.exists(args.target):
        mode = 'a+' if args.append else 'w+'
        output_fp = open(args.output, mode)
        if os.path.isdir(args.target):
            scan_directory(
                args.target, args.prefix, output_fp, 
                next_step=args.next_step,
                unknowns=args.unknowns,
                file_regex=args.file_regex,
                method_regex=args.method_regex,
                verbose=args.verbose,
            )
        else:
            try:
                objc = ObjcHeader(args.target, unknowns=args.unknowns, verbose=args.verbose)
                objc.save_hooks(output_fp, args.method_regex)
                print(INFO+"Generated %d function hooks" % objc._hook_count)
            except:
                print(WARN+"Invalid objective-c header file")
        output_fp.seek(0)
        length = len(output_fp.read())
        output_fp.close()
        print(INFO+"Hooks written to: "+args.output+" (%d bytes)" % length)
    else:
        print(WARN+"File or directory does not exist")
    