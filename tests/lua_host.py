"""Lua 5.4 host helper; does not provide the game's Lua 5.1 runtime."""
import ctypes
LIB=ctypes.CDLL('liblua5.4.so.0')
LIB.luaL_newstate.restype=ctypes.c_void_p
LIB.luaL_openlibs.argtypes=[ctypes.c_void_p]
LIB.luaL_loadbufferx.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_char_p]
LIB.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_longlong,ctypes.c_void_p]
LIB.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)]
LIB.lua_tolstring.restype=ctypes.c_char_p
LIB.lua_close.argtypes=[ctypes.c_void_p]
def run(name,code):
    state=LIB.luaL_newstate();LIB.luaL_openlibs(state);data=code.encode()
    try:
        status=LIB.luaL_loadbufferx(state,data,len(data),name.encode(),None)
        if not status:status=LIB.lua_pcallk(state,0,0,0,0,None)
        if status:
            error=LIB.lua_tolstring(state,-1,None)
            raise AssertionError((name,error.decode() if error else status))
    finally:LIB.lua_close(state)
