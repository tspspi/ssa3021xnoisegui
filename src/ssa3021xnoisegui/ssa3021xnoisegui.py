import argparse
import os
import json
import sys
import logging
import datetime
import timedelta

from pathlib import Path
from time import time

import FreeSimpleGUI as sg
import numpy as np

#import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ssa3021x.ssa3021x import SSA3021X

class NoiseDisplay:
    def __init__(self, cfg, logger):
        self._logger = logger

        self._cfg = cfg

        self._plotsize = (320*2, 240*2)
        self._figures = { }

        self._updateGraphs = True

        self._nextsweeptime = 0

        self._lastsweepf = None
        self._lastsweep = None
        self._snrs = np.full((cfg["sampling"]["storedsamples"],), None)
        self._sigs = np.full((cfg["sampling"]["storedsamples"],), None)

        self._sa = SSA3021X(
            address = cfg["ssa"]["ip"],
            logger = logger
        )
        self._sa._connect(cfg["ssa"]["ip"])
        print(f"Connecting to {self._sa.get_id()}")

    def run(self):
        layout = [
            [
                sg.Canvas(size = self._plotsize, key = "canvRaw"),
                sg.Canvas(size = self._plotsize, key = "canvSignals"),
                sg.Canvas(size = self._plotsize, key = "canvSNR")
            ],
            [ sg.Button("Clear", key="btnClear") ],
            [ sg.Button("Exit", key="btnExit") ]
        ]

        self._window = sg.Window("SSA3021X realtime noise display", layout = layout, finalize = True)

        self._figures = {
            'raw' : self._init_figure('canvRaw', "Frequency [MHz]", "Signal", "Last aquired sweep", grid = True, legend = False),
            'signals' : self._init_figure('canvSignals', "Sample [arb.]", "Peak signal", "Peak signal", grid = True, legend=False),
            'snr' : self._init_figure('canvSNR', "Sample [arb.]", "SNR", "SNR (sliding window)", grid = True, legend = False)
        }

        while True:
            event, value = self._window.read(timeout = 1)
            if event in ('btnExit', None):
                self._sa._disconnect()
                break

            if event in ('btnClear'):
                self._snrs = np.full((self._cfg["sampling"]["storedsamples"],), None)
                self._sigs = np.full((self._cfg["sampling"]["storedsamples"],), None)
                self._updateGraphs = True

            # Check if we should perform a new fetch
            if self._nextsweeptime < time():
                # We query new data
                # Frequencies are in data['frq'] in Hz
                # Data is in data['data'][0]['data'] in volts or dBm

                data = self._sa.query_trace()
                self._lastsweepf = np.asarray(data['frq']) / 1e6
                self._lastsweep = np.asarray(data['data'][0]['data'])

                # Track the peak
                peakamp = np.max(self._lastsweep)

                # Assume left 1/4 and right 1/4 for noise estimation
                noisesamples = np.concatenate((
                    self._lastsweep[:int(len(self._lastsweep)/4)],
                    self._lastsweep[int(3 * len(self._lastsweep) / 4):]
                ))

                self._sigs = np.roll(self._sigs, -1)
                self._snrs = np.roll(self._snrs, -1)

                self._sigs[-1] = peakamp
                self._snrs[-1] = peakamp / np.mean(noisesamples)

                self._nextsweeptime = time() + self._cfg['sampling']['interval']
                print(f"Next sweep time: {self._nextsweeptime}")

                self._updateGraphs = True

            if self._updateGraphs:
                self._updateGraphs = False

                ax = self._figure_begindraw('raw')
                ax.plot(self._lastsweepf, self._lastsweep)
                ax.ticklabel_format(useOffset = False)
                self._figure_enddraw('raw')

                ax = self._figure_begindraw('signals')
                ax.plot(self._sigs)
                ax.ticklabel_format(useOffset = False)
                self._figure_enddraw('signals')

                ax = self._figure_begindraw('snr')
                ax.plot(self._snrs)
                ax.ticklabel_format(useOffset = False)
                self._figure_enddraw('snr')




    def _init_figure(self, canvasName, xlabel, ylabel, title, grid=True, legend=False):
        figTemp = Figure()
        fig = Figure(figsize = ( self._plotsize[0] / figTemp.get_dpi(), self._plotsize[1] / figTemp.get_dpi()) )

        self._figure_colors_fig(fig)

        ax = fig.add_subplot(111)
                
        self._figure_colors(ax)
                
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
 
        if grid:
            ax.grid()
        if legend:
            ax.legend()

        fig_agg = FigureCanvasTkAgg(fig, self._window[canvasName].TKCanvas)
        fig_agg.draw()
        fig_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return {
            'fig' : fig,
            'axis' : ax,
            'fig_agg' : fig_agg,
            'xlabel' : xlabel,
            'ylabel' : ylabel,
            'title' : title,
            'grid' : grid,
            'legend' : legend
        }

    def _figure_begindraw(self, name):
        self._figures[name]['axis'].cla()
        self._figures[name]['axis'].set_xlabel(self._figures[name]['xlabel'])
        self._figures[name]['axis'].set_ylabel(self._figures[name]['ylabel'])
        self._figures[name]['axis'].set_title(self._figures[name]['title'])
        if self._figures[name]['grid']:
            self._figures[name]['axis'].grid()
        self._figure_colors(self._figures[name]['axis'])
        return self._figures[name]['axis']

    def _figure_enddraw(self, name):
        if self._figures[name]['legend']:
            self._figures[name]['axis'].legend()
        self._figures[name]['fig_agg'].draw()

    def _figure_colors_fig(self, fig):
        fig.set_facecolor((0,0,0))

    def _figure_colors(self, ax):
        ax.set_facecolor((0,0,0))
        ax.xaxis.label.set_color((0.77, 0.80, 0.92))
        ax.yaxis.label.set_color((0.77, 0.80, 0.92))
        ax.title.set_color((0.77, 0.80, 0.92))
        for spine in [ 'top', 'bottom', 'left', 'right' ]:
            ax.spines[spine].set_color((0.77,0.80,0.92))
        for axis in [ 'x', 'y' ]:
            ax.tick_params(axis = axis, colors = (0.77, 0.80, 0.92))

       

class WindowConnect:
    def __init__(self, cfg):
        self._cfg = cfg

    def showWindow(self):
        cfg = self._cfg
        layout = [
            [
                sg.Column([
                    [ sg.Text("IP address:") ],
                    [ sg.Text("Window size (samples):") ],
                    [ sg.Text("Sampling interval (s):") ]
                ]),
                sg.Column([
                    [ sg.InputText(cfg['ssa']['ip'], key="txtSSAIp") ],
                    [ sg.InputText(cfg['sampling']['window'], key="txtSamplingWindow") ],
                    [ sg.InputText(cfg['sampling']['interval'], key="txtSamplingInterval") ]
                ])
            ],
            [
                sg.Button("Connect", key="btnConnect"),
                sg.Button("Exit", key="btnAbort")
            ]
        ]
        window = sg.Window("SSA3021X noise estimation", layout, finalize = True)

        while True:
            event, values = window.read(timeout = 10)
            if event in ('btnAbort', None):
                return None
            if event == 'btnConnect':
                try:
                    # Check values ...
                    cfg['sampling']['window'] = int(values["txtSamplingWindow"])
                    if cfg['sampling']['window'] < 2:
                        raise ValueError("Sampling window has to be at least 2 samples long")
                except:
                    ModalDialogError().show("Invalid sampling window", "The supplied sampling window size is invalid")

                try:
                    cfg['sampling']['interval'] = float(values["txtSamplingInterval"])
                    if cfg['sampling']['interval'] < 0:
                        raise ValueError("Sampling interval has to be a positive number or zero")
                except:
                    ModalDialogError().show("Invalid sampling interval", "The supplied sampling interval is invalid")

                cfg['ssa']['ip'] = values["txtSSAIp"]

                window.close()
                return cfg



class ModalDialogError:
    def __init__(self):
        pass

    def show(self, title, message):
        layout = [
                [ sg.Text(message) ],
                [ sg.Button("Ok", key="btnOk") ]
            ]
        window = sg.Window(title, layout, finalize = True)
        window.TKroot.transient()
        window.TKroot.grab_set()
        window.TKroot.focus_force()

        while True:
            event, values = window.read()
            if event in ('btnOk', None):
                window.close()
                return None

class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.__str__()
        if isinstance(obj, timedelta):
            return obj.__str__()
        return json.JSONEncoder.default(self, obj)

def recursiveApplyDictUpdate(original, additional):
    for k in original:
        if k in additional:
            if not isinstance(original[k], dict):
                original[k] = additional[k]
            else:
                original[k] = recursiveApplyDictUpdate(original[k], additional[k])
    return original

def main():
    logger = logging.getLogger()

    # Parse CLI arguments
    ap = argparse.ArgumentParser(description = "SSA3021X realtime noise estimatior GUI")
    ap.add_argument("--cfg", type=str, required=False, default=None, help="Configuration file to store defaults. Defaults to ~/.config/ssa3021xrealtimenoisegui.cfg")

    ap.add_argument("--ssaip", type=str, required=False, default=None, help="Override default IP from SSA")
    ap.add_argument("--samplewindow", type=int, required=False, default=None, help="Override sampling window size (samples)")
    ap.add_argument("--sampleinterval", type=float, required=False, default=None, help="Override sampling interval (s)")
    ap.add_argument("--connect", action="store_true", help="Skip connect dialog and use supplied or configured options")

    args = ap.parse_args()

    # First start with default configuration

    cfg = {
        "ssa" : {
            "ip" : None
        },
        "sampling" : {
            "window" : 10,
            "interval" : 1,
            "storedsamples" : 1000
        },
        "connect" : False
    }

    # If we have some load configuration file ...

    cfgfile = args.cfg
    if cfgfile is None:
        cfgfile = os.path.join(Path.home(), ".config/ssa3021xrealtimenoisegui.cfg")
    try:
        with open(cfgfile) as cfile:
            cfgs_in_file = json.load(cfile)
    except Exception as e:
        cfgs_in_file = { }
        print(f"Failed to load configuration file {cfgfile}")
        print(e)

    # Apply ...

    cfg = recursiveApplyDictUpdate(cfg, cfgs_in_file)

    # Apply overrides from CLI

    if args.ssaip is not None:
        cfg["ssa"]["ip"] = args.ssaip
    if args.samplewindow is not None:
        cfg["sampling"]["window"] = args.samplewindow
    if args.sampleinterval is not None:
        cfg["sampling"]["interval"] = args.sampleinterval

    if not args.connect:
        # We display the configuration window
        wnd = WindowConnect(cfg)
        cfg = wnd.showWindow()
        if cfg is None:
            sys.exit(0)

    # Now start the actual application

    mainWnd = NoiseDisplay(cfg, logger)
    mainWnd.run()

if __name__ == "__main__":
    main()
