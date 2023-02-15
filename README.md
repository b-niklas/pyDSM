## **pyDSM**: Discrete Slip-link Model (DSM) in Python for Fast Quantitative Rheology Predictions of Entangled Polymers

<br> 

**Reference:** Ethier, Jeffrey G.; C&oacute;rdoba, Andr&eacute;s; Schieber, Jay D. "pyDSM: Fast Quantitative Rheology Predictions for Entangled Polymers in Python", Computer Physics Communications, submitted.

---

### Installation:

<br>

(1) Create anaconda environment with dependencies:

```
conda create env --file environment.yml
```

(2) Activate conda environment:

```
conda activate pydsm-env
```

<br>


### Running a simulation:

<br>

(1) Set input parameters in input.yaml

(2) Run the program
```
python gpu_dsm.py
```

<br>

POSITIONAL ARGUMENTS:

sim_ID - An integer for the simulation ID. Appended to the filenames. 

Example: 
```
python gpu_dsm.py 1
```

<br>

FLAG ARGUMENTS:

```
-h, --help - show help message and exit
-d [device_num] - if multiple GPUs are present, select device number
-c [otf] - force simulation to use on-the-fly (otf) correlator, but correlation errors will not be reported
-o [output_dir] - specify output directory
--fit - a flag to turn on G(t) fitting after simulation is done. 
--distr - a flag to save initial and final Q, Lpp, and Z distributions to file.
```

If the --fit flag is not used, G(t) fits can be done by importing the class in a new Python file:
```
from core.fit import CURVE_FIT

filepath='path/to/Gt_result.txt'
output_path = 'path/to/fit/results/'
gt_fit = CURVE_FIT(filepath,output_path)
gt_fit.fit()
```
