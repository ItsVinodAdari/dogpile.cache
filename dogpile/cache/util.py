import sha1
import inspect

class PluginLoader(object):
    def __init__(self, group):
        self.group = group
        self.impls = {}

    def load(self, name):
        if name in self.impls:
             return self.impls[name]()
        else:
            import pkg_resources
            for impl in pkg_resources.iter_entry_points(
                                self.group, 
                                name):
                self.impls[name] = impl.load
                return impl.load()
            else:
                raise Exception(
                        "Can't load plugin %s %s" % 
                        (self.group, name))

    def register(self, name, modulepath, objname):
        def load():
            mod = __import__(modulepath)
            for token in modulepath.split(".")[1:]:
                mod = getattr(mod, token)
            return getattr(mod, objname)
        self.impls[name] = load


def function_key_generator(fn):
    """Return a function that generates a string
    key, based on a given function as well as
    arguments to the returned function itself.
    
    This is used by :meth:`.CacheRegion.cache_on_arguments`
    to generate a cache key from a decorated function.
    
    It can be replaced using the ``function_key_generator``
    argument passed to :func:`.make_region`.
    
    """

    kls = None
    if hasattr(fn, 'im_func'):
        kls = fn.im_class
        fn = fn.im_func

    if kls:
        namespace = '%s.%s' % (kls.__module__, kls.__name__)
    else:
        namespace = '%s|%s' % (inspect.getsourcefile(fn), fn.__name__)

    args = inspect.getargspec(fn)
    has_self = args[0] and args[0][0] in ('self', 'cls')
    def generate_key(*args, **kw):
        if kw:
            raise ValueError(
                    "dogpile.cache's default key creation "
                    "function does not accept keyword arguments.")
        if has_self:
            args = args[1:]
        return namespace + "|" + " ".join(map(unicode, args))
    return generate_key

def sha1_mangle_key(key):
    """a SHA1 key mangler."""

    return sha1(key).hexdigest()

def length_conditional_mangler(length, mangler):
    """a key mangler that mangles if the length of the key is
    past a certain threshold.
    
    """
    def mangle(key):
        if len(key) >= length:
            return mangler(key)
        else:
            return key
    return mangle