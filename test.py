# create debug file
$code = @'
import traceback, sys, os
print("Python:", sys.executable)
print("cwd:", os.getcwd())
print("sys.path[0]:", sys.path[0])
try:
    from ml.agentic.orchestrator import SafetyOrchestrator
    print("IMPORT OK: ml.agentic.orchestrator found")
    try:
        print("Instantiating SafetyOrchestrator() ...")
        o = SafetyOrchestrator()
        print("INSTANTIATION OK:", type(o))
    except Exception as e:
        print("Instantiation failed:")
        traceback.print_exc()
except Exception:
    print("Import failed:")
    traceback.print_exc()
'@
Set-Content -Path .\orch_debug.py -Value $code -Encoding UTF8