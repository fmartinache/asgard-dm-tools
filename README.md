# asgard-dm-tools
User tools to interact in the laboratory with the Asgard DMs

At least for now, a PyQt5 GUI designed to control one of the four deformable mirrors of the ASGARD instrument suite, assuming that the corresponding Asgard DM server is running and that at least two DM channels are set up. And a turbulence simulator prototype.

## Installation

> pip install asgard_lab_DM_tools -U

## Usage

Pip installs a GUI that can be called from the Linux CLI using the following command:

> lab-MDM-control &

that takes no argument and uses tabs to control from the same GUI the 4 Asgard DMs.
This replaces the previous single-DM GUI that will eventually be dropped out of the distribution:

> lab-DM-control 1&

to connect to the Asgard DM server #1.

The GUI is otherwise simple and should be self-explanatory to somebody who knows what it is designed for!

As well as a turbulence_simulation script also to be called from the Linux CLI

> turbulence-simulator
