"""The optional bytecode cache system. This is useful if you have very
complex template situations and the compilation of all those templates
slows down your application too much.

Situations where this is useful are often forking web applications that
are initialized on the first request.
"""
import errno
import fnmatch
import marshal
import os
import pickle
import stat
import sys
import tempfile
import typing as t
from hashlib import sha1
from io import BytesIO
from types import CodeType
if t.TYPE_CHECKING:
    import typing_extensions as te
    from .environment import Environment


    class _MemcachedClient(te.Protocol):
        pass
bc_version = 5
bc_magic = b'j2' + pickle.dumps(bc_version, 2) + pickle.dumps(sys.
    version_info[0] << 24 | sys.version_info[1], 2)


class Bucket:
    """Buckets are used to store the bytecode for one template.  It's created
    and initialized by the bytecode cache and passed to the loading functions.

    The buckets get an internal checksum from the cache assigned and use this
    to automatically reject outdated cache material.  Individual bytecode
    cache subclasses don't have to care about cache invalidation.
    """

    def __init__(self, environment: 'Environment', key: str, checksum: str
        ) ->None:
        self.environment = environment
        self.key = key
        self.checksum = checksum
        self.reset()

    def reset(self) ->None:
        """Resets the bucket (unloads the bytecode)."""
        self.code = None

    def load_bytecode(self, f: t.BinaryIO) ->None:
        """Loads bytecode from a file or file like object."""
        code = marshal.load(f)
        if isinstance(code, CodeType):
            self.code = code

    def write_bytecode(self, f: t.IO[bytes]) ->None:
        """Dump the bytecode into the file or file like object passed."""
        if self.code is not None:
            marshal.dump(self.code, f)

    def bytecode_from_string(self, string: bytes) ->None:
        """Load bytecode from bytes."""
        f = BytesIO(string)
        self.load_bytecode(f)

    def bytecode_to_string(self) ->bytes:
        """Return the bytecode as bytes."""
        if self.code is None:
            return b""
        f = BytesIO()
        self.write_bytecode(f)
        return f.getvalue()


class BytecodeCache:
    """To implement your own bytecode cache you have to subclass this class
    and override :meth:`load_bytecode` and :meth:`dump_bytecode`.  Both of
    these methods are passed a :class:`~jinja2.bccache.Bucket`.

    A very basic bytecode cache that saves the bytecode on the file system::

        from os import path

        class MyCache(BytecodeCache):

            def __init__(self, directory):
                self.directory = directory

            def load_bytecode(self, bucket):
                filename = path.join(self.directory, bucket.key)
                if path.exists(filename):
                    with open(filename, 'rb') as f:
                        bucket.load_bytecode(f)

            def dump_bytecode(self, bucket):
                filename = path.join(self.directory, bucket.key)
                with open(filename, 'wb') as f:
                    bucket.write_bytecode(f)

    A more advanced version of a filesystem based bytecode cache is part of
    Jinja.
    """

    def load_bytecode(self, bucket: Bucket) ->None:
        """Subclasses have to override this method to load bytecode into a
        bucket.  If they are not able to find code in the cache for the
        bucket, it must not do anything.
        """
        raise NotImplementedError()

    def dump_bytecode(self, bucket: Bucket) ->None:
        """Subclasses have to override this method to write the bytecode
        from a bucket back to the cache.  If it unable to do so it must not
        fail silently but raise an exception.
        """
        raise NotImplementedError()

    def clear(self) ->None:
        """Clears the cache.  This method is not used by Jinja but should be
        implemented to allow applications to clear the bytecode cache used
        by a particular environment.
        """
        raise NotImplementedError()

    def get_cache_key(self, name: str, filename: t.Optional[t.Union[str]]=None
        ) ->str:
        """Returns the unique hash key for this template name."""
        return sha1(f"{name}|{filename}".encode("utf-8")).hexdigest()

    def get_source_checksum(self, source: str) ->str:
        """Returns a checksum for the source."""
        return sha1(source.encode("utf-8")).hexdigest()

    def get_bucket(self, environment: 'Environment', name: str, filename: t
        .Optional[str], source: str) ->Bucket:
        """Return a cache bucket for the given template.  All arguments are
        mandatory but filename may be `None`.
        """
        key = self.get_cache_key(name, filename)
        checksum = self.get_source_checksum(source)
        return Bucket(environment, key, checksum)

    def set_bucket(self, bucket: Bucket) ->None:
        """Put the bucket into the cache."""
        self.dump_bytecode(bucket)


class FileSystemBytecodeCache(BytecodeCache):
    """A bytecode cache that stores bytecode on the filesystem.  It accepts
    two arguments: The directory where the cache items are stored and a
    pattern string that is used to build the filename.

    If no directory is specified a default cache directory is selected.  On
    Windows the user's temp directory is used, on UNIX systems a directory
    is created for the user in the system temp directory.

    The pattern can be used to have multiple separate caches operate on the
    same directory.  The default pattern is ``'__jinja2_%s.cache'``.  ``%s``
    is replaced with the cache key.

    >>> bcc = FileSystemBytecodeCache('/tmp/jinja_cache', '%s.cache')

    This bytecode cache supports clearing of the cache using the clear method.
    """

    def __init__(self, directory: t.Optional[str]=None, pattern: str=
        '__jinja2_%s.cache') ->None:
        if directory is None:
            directory = self._get_default_cache_dir()
        self.directory = directory
        self.pattern = pattern

    def _get_default_cache_dir(self) ->str:
        if sys.platform == 'win32':
            return os.path.join(tempfile.gettempdir(), 'jinja2_cache')
        else:
            return os.path.join(tempfile.gettempdir(), f'jinja2_cache_{os.getuid()}')

    def _get_cache_filename(self, bucket: Bucket) ->str:
        return os.path.join(self.directory, self.pattern % bucket.key)

    def load_bytecode(self, bucket: Bucket) ->None:
        filename = self._get_cache_filename(bucket)
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                bucket.load_bytecode(f)

    def dump_bytecode(self, bucket: Bucket) ->None:
        filename = self._get_cache_filename(bucket)
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'wb') as f:
                bucket.write_bytecode(f)
        except OSError as e:
            raise OSError(f'Unable to write bytecode cache file: {e}')

    def clear(self) ->None:
        for filename in os.listdir(self.directory):
            if fnmatch.fnmatch(filename, self.pattern % '*'):
                try:
                    os.remove(os.path.join(self.directory, filename))
                except OSError:
                    pass


class MemcachedBytecodeCache(BytecodeCache):
    """This class implements a bytecode cache that uses a memcache cache for
    storing the information.  It does not enforce a specific memcache library
    (tummy's memcache or cmemcache) but will accept any class that provides
    the minimal interface required.

    Libraries compatible with this class:

    -   `cachelib <https://github.com/pallets/cachelib>`_
    -   `python-memcached <https://pypi.org/project/python-memcached/>`_

    (Unfortunately the django cache interface is not compatible because it
    does not support storing binary data, only text. You can however pass
    the underlying cache client to the bytecode cache which is available
    as `django.core.cache.cache._client`.)

    The minimal interface for the client passed to the constructor is this:

    .. class:: MinimalClientInterface

        .. method:: set(key, value[, timeout])

            Stores the bytecode in the cache.  `value` is a string and
            `timeout` the timeout of the key.  If timeout is not provided
            a default timeout or no timeout should be assumed, if it's
            provided it's an integer with the number of seconds the cache
            item should exist.

        .. method:: get(key)

            Returns the value for the cache key.  If the item does not
            exist in the cache the return value must be `None`.

    The other arguments to the constructor are the prefix for all keys that
    is added before the actual cache key and the timeout for the bytecode in
    the cache system.  We recommend a high (or no) timeout.

    This bytecode cache does not support clearing of used items in the cache.
    The clear method is a no-operation function.

    .. versionadded:: 2.7
       Added support for ignoring memcache errors through the
       `ignore_memcache_errors` parameter.
    """

    def __init__(self, client: '_MemcachedClient', prefix: str=
        'jinja2/bytecode/', timeout: t.Optional[int]=None,
        ignore_memcache_errors: bool=True):
        self.client = client
        self.prefix = prefix
        self.timeout = timeout
        self.ignore_memcache_errors = ignore_memcache_errors

    def load_bytecode(self, bucket: Bucket) ->None:
        try:
            code = self.client.get(self.prefix + bucket.key)
            if code is not None:
                bucket.bytecode_from_string(code)
        except Exception:
            if not self.ignore_memcache_errors:
                raise

    def dump_bytecode(self, bucket: Bucket) ->None:
        try:
            args = [self.prefix + bucket.key, bucket.bytecode_to_string()]
            if self.timeout is not None:
                args.append(self.timeout)
            self.client.set(*args)
        except Exception:
            if not self.ignore_memcache_errors:
                raise

    def clear(self) ->None:
        # Memcached doesn't support clearing specific keys, so this is a no-op
        pass
