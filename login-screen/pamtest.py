#!/usr/bin/env python3
"""Drive a PAM auth stack from a private config directory with scripted prompt responses.

usage: pamtest.py CONFDIR SERVICE USER MAX_SECONDS [RESPONSE ...]
Each RESPONSE answers one prompt in order; further prompts get an empty response.
"""
import ctypes, os, signal, sys, time
from ctypes import POINTER, Structure, CFUNCTYPE, c_int, c_char_p, c_void_p, byref, cast

confdir, service, user, max_s = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
responses = list(sys.argv[5:])
libpam = ctypes.CDLL("libpam.so.0")
libc = ctypes.CDLL(None)
libc.calloc.restype = c_void_p
libc.strdup.restype = c_void_p
libc.strdup.argtypes = [c_char_p]

class Msg(Structure):
    _fields_ = [("style", c_int), ("msg", c_char_p)]
class Resp(Structure):
    _fields_ = [("resp", c_void_p), ("retcode", c_int)]
CONV = CFUNCTYPE(c_int, c_int, POINTER(POINTER(Msg)), POINTER(POINTER(Resp)), c_void_p)
class Conv(Structure):
    _fields_ = [("conv", CONV), ("appdata", c_void_p)]

STYLE = {1: "PROMPT(secret)", 2: "PROMPT(echo)", 3: "ERROR", 4: "INFO"}
t0 = time.time()
def log(*a): print("%6.2fs" % (time.time() - t0), *a, flush=True)

@CONV
def conv(n, msgs, resp, _):
    arr = cast(libc.calloc(n, ctypes.sizeof(Resp)), POINTER(Resp))
    for i in range(n):
        m = msgs[i].contents
        log(STYLE.get(m.style, m.style), (m.msg or b"").decode(errors="replace").strip())
        if m.style in (1, 2):
            r = responses.pop(0) if responses else ""
            log("  -> responding with", "(empty)" if r == "" else "(%d chars)" % len(r))
            arr[i].resp = libc.strdup(r.encode())
    resp[0] = arr
    return 0

c = Conv(conv, None)
h = c_void_p()
libpam.pam_start_confdir.argtypes = [c_char_p, c_char_p, POINTER(Conv), c_char_p, POINTER(c_void_p)]
rc = libpam.pam_start_confdir(service.encode(), user.encode(), byref(c), confdir.encode(), byref(h))
if rc != 0: sys.exit("pam_start_confdir failed: %d" % rc)
# pam_fprintd gives up its wait on SIGINT, which keeps a test from waiting for a finger forever
signal.signal(signal.SIGALRM, lambda *a: os.kill(os.getpid(), signal.SIGINT))
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.alarm(max_s)
libpam.pam_authenticate.argtypes = [c_void_p, c_int]
rc = libpam.pam_authenticate(h, 0)
libpam.pam_strerror.restype = c_char_p
libpam.pam_strerror.argtypes = [c_void_p, c_int]
log("RESULT", rc, libpam.pam_strerror(h, rc).decode())
libpam.pam_end.argtypes = [c_void_p, c_int]
libpam.pam_end(h, rc)
