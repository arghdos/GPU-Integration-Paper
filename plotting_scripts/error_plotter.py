#! /usr/bin/env python2.7
import matplotlib
import numpy as np
import os
import sys
import plot_styles as ps
from data_parser import data_series
import matplotlib.pyplot as plt
import re
import os
from optionloop import OptionLoop

series_list = []
PaSR = None
opt = None
smem = None
timestep = None

lines = []
files = [f for f in os.listdir(ps.datapath) if f.endswith('logfile')
            and os.path.isfile(os.path.join(ps.datapath, f))]
for f in files:
    with open(os.path.join(ps.datapath, f), 'r') as file:
        lines = [l.strip() for l in file.readlines() if l.strip()]

    for line in lines:
        if not line.strip():
            continue
        if 'lang' in line:
            lang = line[line.index(':') + 1:]
            continue
        if 'PaSR ICs' in line:
            PaSR = True
            continue
        elif 'Same ICs' in line:
            PaSR = False
            continue
        match = re.search(r'cache_opt:\s*(\w+)', line)
        if match:
            opt = match.group(1) == 'True'
            continue
        match = re.search(r'shared_mem:\s*(\w+)', line)
        if match:
            smem = match.group(1) == 'True'
            continue
        match = re.search(r't_step=(\d+e(?:-)?\d+)', line)
        if match:
            timestep = float(match.group(1))
            continue
        match = re.search(r'log/([\w\d-]+)-log.bin', line)
        if match:
            solver = match.group(1)
            solver = solver[:solver.index('-int')]
            if 'nokry' in f:
                solver += 'nk'
            continue
        match = re.search(r'L2 \(max, mean\) = (nan, nan)', line)
        match2 = re.search(r'L2 \(max, mean\) = (\d+\.\d+e(?:[+-])?\d+)', line)
        if match or match2:
            yval = np.nan if (match and not match2) else float(match2.group(1))
            test = data_series(solver, gpu=lang=='cuda', cache_opt=opt, smem=smem, finite_difference=False)
            series = next((x for x in series_list if x == test), None)
            if series is None:
                series_list.append(test)
                series = test
            series.add_x_y(1e-6 / timestep, yval)
            continue
        if 'Linf' in line:
            continue
        raise Exception(line)

c_params = OptionLoop({'gpu' : False,
            'opt' : [True, False],
            'same_ics' : [False]}, lambda: False)
cuda_params = OptionLoop({'gpu' : True,
            'opt' : [True, False],
            'smem' : [True, False],
            'same_ics' : [False]}, lambda: False)

op = c_params + cuda_params
for state in op:
    gpu = state['gpu']
    opt = state['opt']
    smem = state['smem']

    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.set_xscale("log", nonposx='clip')
    ax.set_yscale("log", nonposy='clip')

    data_list = [x for x in series_list if x.gpu == gpu and
                    x.cache_opt == opt and x.smem == smem]

    name_list = []
    for s in sorted(data_list, key = lambda x: x.name):
        nk = 'nk' in s.name
        if nk:
            if 'radau' in s.name:
                continue
            name = s.name[:s.name.index('nk')]
            s.name = s.name[:s.name.index('nk')] + ' (exact)'
        else:
            name = s.name

        name_list = set(name_list).union([name])
        marker, dummy = ps.marker_dict[name]
        if nk and 'exp4' in name:
            marker = '.'
        color = ps.color_dict[name]
        marker_style = ps.clear_marker_style if not nk else ps.marker_style
        s.set_clear_marker(marker=marker, color=color, **marker_style)
        #else:
        #    s.set_marker(marker=marker, color=color, **ps.marker_style)
        #s.set_clear_marker(marker=marker, color=color, **ps.clear_marker_style)
        s.plot(ax, ps.pretty_names, zorder=10 if nk and 'exp4' in name else None)

    #draw order lines
    if not gpu and not opt:
        plt.plot([1e2, 1e3], [1.7, 0.17], 'k')
        plt.text(6.5e1, 0.35, r"Order--1")

        plt.plot([1.5e1, 1.5e2], [0.06, 0.0006], 'k')
        plt.text(4.5e1, 0.0075, r"Order--2")

        plt.plot([1.8, 1.8e1], [1.5e-1, 1.5e-4], 'k')
        plt.text(6, 4e-3, r"Order--3")

        plt.plot([0.5, 5], [2e-1, 2e-5], 'k')
        plt.text(2.5e-1, 1e-3, r"Order--4")

        plt.text(1e3, 4e-4, r"``Exact'' Krylov")
        plt.text(1e3, 2e0, r"Approximate Krylov", rotation=-40)

    plt.xlabel(r'Steps taken')
    plt.ylabel(r'Maximum error, $\left\lvert\textbf{E}\right\rvert$')

    artists = []
    labels = []
    for name in name_list:
        color = ps.color_dict[name]
        show = ps.pretty_names(name)
        artist = plt.Line2D((0,1),(0,0),
            markerfacecolor='none', marker=ps.marker_dict[name][0],
            markeredgecolor=color, linestyle='',
            markersize=15)
        artists.append(artist)
        labels.append(show)

    plt.legend(artists, labels, **ps.legend_style)
    ax.set_xlim((1.5e-1, 5e6))
    ps.finalize()

    plt.savefig(os.path.join(ps.figpath,
        '{}_{}_{}_error.pdf'.format(
        'c' if not gpu else 'cuda',
        'co' if opt else 'nco',
        'smem' if smem else 'nosmem')))
    plt.close()
