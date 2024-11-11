# Graphical user interface for noise estimation using SSA3021X

Simple graphical frontend for an SSA3021X spectrum analyzer to
perform simple noise measurements. It assumes one measures a single
peak against background.

![Connect window](https://raw.githubusercontent.com/tspspi/ssa3021xnoisegui/refs/heads/master/doc/wndconnect.png)

![Measurement window (noise measurement)](https://raw.githubusercontent.com/tspspi/ssa3021xnoisegui/refs/heads/master/doc/wndmeasurement_noise.png)

![Measurement window (signal measurement)](https://raw.githubusercontent.com/tspspi/ssa3021xnoisegui/refs/heads/master/doc/wndmeasurement_signal.png)

The utility requires the spectrum analyzer to:

* Be set to linear scale (this will be fixed in later versions)
* The center frequency should be set to the desired signal frequency.
  The program picks the largest peak as signal though.
* The quarter of samples on the left and to the right of the span is
  used as basis to calculate the noise floor of the signal.

## Installation

This package can be installed simply via ```pip```

```
pip install ssa3021xnoisegui-tspspi
```

## Usage

```
ssa3021xnoisegui
```

## Configuration file

One can pre-set some configuration variables in a configuration
file at ```~/.config/ssa3021xrealtimenoisegui.cfg```. All variables
are optional:

```
{
	"ssa" : {
		"ip" : "10.4.1.18"
	},
    "sampling" : {
        "window" : 10,
        "interval" : 0.5,
        "storedsamples" : 1000
    }
}

```
