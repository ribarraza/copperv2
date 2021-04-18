#!/usr/bin/env python

import sys
import argparse
from pathlib import Path
import subprocess
import time

root=Path('.')
work_dir=root/'work'
work_dir.mkdir(exist_ok=True)

chisel_work_dir=work_dir/'chisel'
sim_work_dir=work_dir/'sim'

steps = dict(
    chisel = f'./scripts/chisel.sh "runMain gcd.GCDDriver --target-dir {chisel_work_dir}"',
    sim_build = [
        f"./scripts/verilator.sh cmake -f ./scripts/CMakeLists.txt -B {sim_work_dir}",
        f"./scripts/verilator.sh cmake --build {sim_work_dir}",
    ],
    sim_run = dict(args="./Vour",cwd=sim_work_dir),
)
step_list = list(steps.keys())

parser = argparse.ArgumentParser(description='Run stuff.')
parser.add_argument('-from', type=str, choices=step_list, default=step_list[0], dest='_from',
                    help='Run from this step')
parser.add_argument('-to', type=str, choices=step_list, default=step_list[-1],
                    help='Run to this step')

args = parser.parse_args()

for step in step_list[step_list.index(args._from):step_list.index(args.to)]:
    commands = steps[step]
    run_opts = dict(shell=True,check=True,encoding='utf-8')
    if isinstance(commands,dict):
        cmd = commands.pop('args')
        run_opts.update(commands)
    else:
        cmd = commands
    if isinstance(cmd,str):
        cmd = [cmd]
    for c in cmd:
        print(f"{step}> {c}")
        try:
            subprocess.run(c,**run_opts)
        except KeyboardInterrupt:
            time.sleep(1)
            print('\nrun.py: Keyboard interrupt')
            sys.exit(1)
        except subprocess.CalledProcessError:
            print('run.py: Called process error')
            sys.exit(1)


