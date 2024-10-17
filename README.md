# asgard-dm-tools
User tools to interact in the laboratory with the Asgard DMs

At least for now, a PyQt5 GUI designed to control one of the four deformable mirrors of the ASGARD instrument suite, assuming that the corresponding Asgard DM server is running and that at least two DM channels are set up.

## Installation

> pip install asgard_lab_DM_controller

## Usage

Pip installs a GUI that can be called from the Linux CLI using the following command:

> lab-DM-control 1&

that will attempt to connect to the Asgard DM server #1.

The GUI is otherwise simple and should be self-explanatory to somebody who knows what it is designed for!

