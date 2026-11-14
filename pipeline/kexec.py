"""Send a code file to the running kernel and print its output. Usage: kexec.py file.py [file2.py ...]"""
import sys, os
from jupyter_client import BlockingKernelClient

HERE = os.path.dirname(os.path.abspath(__file__))
kc = BlockingKernelClient(connection_file=os.path.join(HERE, 'kernel.json'))
kc.load_connection_file()
kc.start_channels()
kc.wait_for_ready(timeout=30)

for path in sys.argv[1:]:
    code = open(path).read()
    msg_id = kc.execute(code)
    while True:
        msg = kc.get_iopub_msg(timeout=3600)
        if msg['parent_header'].get('msg_id') != msg_id:
            continue
        t, c = msg['msg_type'], msg['content']
        if t == 'stream':
            sys.stdout.write(c['text'])
        elif t in ('execute_result', 'display_data'):
            data = c['data']
            sys.stdout.write(data.get('text/plain', '[non-text output]') + '\n')
        elif t == 'error':
            sys.stdout.write('\n'.join(c['traceback']) + '\n')
            sys.exit(1)
        elif t == 'status' and c['execution_state'] == 'idle':
            break
