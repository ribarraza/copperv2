#!/usr/bin/env python

import os
import sys
import argparse
from pathlib import Path
import subprocess
import time

# unbuffered output
class Unbuffered:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)
sys.stdout = Unbuffered(sys.stdout)

def run(c,run_opts,step):
    echo = f"run.py-info: {step}> {c}"
    if 'cwd' in run_opts:
        echo = echo + f' # cwd: {run_opts["cwd"]}'
    print(echo)
    try:
        subprocess.run(c,**run_opts)
    except KeyboardInterrupt:
        time.sleep(1)
        print('\nrun.py-error: Keyboard interrupt')
        sys.exit(1)
    except subprocess.CalledProcessError:
        print('run.py-error: Called process error')
        sys.exit(1)

root=Path('.')
work_dir=root/'work'
work_dir.mkdir(exist_ok=True)

chisel_work_dir=work_dir/'chisel'
sim_work_dir=work_dir/'sim'
sim_work_dir.mkdir(exist_ok=True)

steps = dict(
    chisel = f'sbt "runMain Copperv2Driver"',
    test = dict(args=[
        f'ln -fs ../../scripts/cocotb.mk ./Makefile',
        'make 2>&1 | tee sim.log',
        r'sed -r -i "s/[[:cntrl:]]\[[0-9]{1,3}m//g" sim.log'],
            cwd=sim_work_dir,
            env={
                "PYTHONPATH":str((root/'sim').resolve()),
                "PYTHONPYCACHEPREFIX":str(sim_work_dir.resolve()/'__pycache__'),
            }
        ),
)
step_list = list(steps.keys())

parser = argparse.ArgumentParser(description='Run stuff.')
parser.add_argument('-from', type=str, choices=step_list, default=step_list[0], dest='_from',
                    help='Run from this step')
parser.add_argument('-to', type=str, choices=step_list, default=step_list[-1],
                    help='Run to this step')
parser.add_argument('-chisel', action='store_true',
                    help='Launch chisel interactive shell (sbt)')
parser.add_argument('-cocotb_reduced', action='store_true',
                    help='Launch cocotb in reduced log mode')
parser.add_argument('-cocotb_debug', action='store_true',
                    help='Launch cocotb in debug log mode')
parser.add_argument('-lint', action='store_true',
                    help='Lint Python')

args = parser.parse_args()

default_run_opts = dict(
    shell=True,
    check=True,
    encoding='utf-8',
    env = os.environ,
)

if args.chisel:
    run('sbt',default_run_opts,'chisel_shell')
    sys.exit(0)

if args.lint:
    run("flake8 sim",default_run_opts,'lint')
    sys.exit(0)

if args.cocotb_debug:
    default_run_opts['env']["DEBUG_TEST"] = "1"

if args.cocotb_reduced:
    default_run_opts['env']["COCOTB_REDUCED_LOG_FMT"] = "1"

for step in step_list[step_list.index(args._from):step_list.index(args.to)+1]:
    commands = steps[step]
    run_opts = default_run_opts
    if isinstance(commands,dict):
        cmd = commands.pop('args')
        if 'env' in commands:
            new = commands.pop('env')
            if "env" in run_opts:
                run_opts["env"].update(new)
            else:
                run_opts["env"] = new
        run_opts.update(commands)
    else:
        cmd = commands
    if isinstance(cmd,str):
        cmd = [cmd]
    for c in cmd:
        run(c,run_opts,step)


