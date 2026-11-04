"""Lua 5.4 test host; this is not Rome II's embedded Lua 5.1 runtime."""
import ctypes
import os
import sys

try:
    LIB = ctypes.CDLL(os.environ.get('RDP_LUA_LIBRARY', 'liblua5.4.so.0'))
except OSError as error:
    raise RuntimeError('Lua 5.4 shared library is required. See docs/build.md or set RDP_LUA_LIBRARY.') from error
LIB.lua_version.argtypes = [ctypes.c_void_p]
LIB.lua_version.restype = ctypes.c_double
if LIB.lua_version(None) != 504:
    raise RuntimeError('The test host requires Lua 5.4, not the game or mod DLL.')
LIB.luaL_newstate.restype = ctypes.c_void_p
LIB.luaL_openlibs.argtypes = [ctypes.c_void_p]
LIB.luaL_loadbufferx.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p]
LIB.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
LIB.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
LIB.lua_tolstring.restype = ctypes.c_char_p
LIB.lua_close.argtypes = [ctypes.c_void_p]
HOST_RUNTIME = 'Lua 5.4 / ' + sys.platform + ' / standalone shared-library test host'


def run(name, code, syntax_only=False):
    state = LIB.luaL_newstate()
    if not state:
        raise MemoryError('Cannot create the Lua test state.')
    data = code.encode('utf-8')
    try:
        LIB.luaL_openlibs(state)
        status = LIB.luaL_loadbufferx(state, data, len(data), name.encode('utf-8'), None)
        if not status and not syntax_only:
            status = LIB.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            error = LIB.lua_tolstring(state, -1, None)
            raise AssertionError((name, error.decode('utf-8', 'replace') if error else status))
    finally:
        LIB.lua_close(state)
