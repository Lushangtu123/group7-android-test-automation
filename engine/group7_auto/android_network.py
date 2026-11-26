"""Bounded device-side hostname connectivity probe; no prompt or account data."""
import re
import subprocess
import time
from datetime import datetime, timezone


def check_android_network(adb, device, run=subprocess.run):
    command=[adb,'-s',device,'shell','toybox','nc','-w','5',
             'connectivitycheck.gstatic.com','80']
    request='GET /generate_204 HTTP/1.1\r\nHost: connectivitycheck.gstatic.com\r\nConnection: close\r\n\r\n'
    start=time.monotonic()
    observation={'started_utc':datetime.now(timezone.utc).isoformat(),
                 'command':command,'endpoint':'http://connectivitycheck.gstatic.com/generate_204',
                 'hostname_http_204':False,'probe_retries':0,
                 'limitation':'Tests device DNS and public HTTP reachability; does not prove either application backend is healthy'}
    try:
        result=run(command,input=request,capture_output=True,text=True,timeout=8)
        first=result.stdout.splitlines()[0] if result.stdout.splitlines() else ''
        ok=result.returncode==0 and bool(re.fullmatch(r'HTTP/1\.[01] 204(?: .*)?',first))
        observation.update(hostname_http_204=ok,status='HTTP_204_OK' if ok else 'NETWORK_PROBE_FAILED',
                           exit_code=result.returncode,stdout=result.stdout[:2048],stderr=result.stderr[:2048])
    except subprocess.TimeoutExpired:
        observation.update(status='PROBE_TIMEOUT',exit_code=None)
    observation['duration_seconds']=round(time.monotonic()-start,3)
    return observation
