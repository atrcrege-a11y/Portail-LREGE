import subprocess, os, sys
base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
subprocess.Popen([os.path.join(base, "LANCER_PORTAIL.bat")], shell=True, cwd=base)