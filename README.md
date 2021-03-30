# A Simple simulation data creator and database manager
A python module for creation and management of simple simulation data.
Essentially, a very basic database manager that creates its own data.


[![LICENSE : MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation
We do not yet have an uploaded version on pypi.
To install you have to clone the repository and then use the package manager [pip](https://pip.pypa.io/en/stable/).
> You need python3 to install this module

```bash
git clone https://github.com/mwiesenberger/simplesimdb
cd path/to/simplesimdb
pip install -e . # editable installation of the module
pytest . # run the unittests
```

## Usage
Use this module if you have (i) an executable (the simulation code) that takes a set of input parameters
and generates a single output file and (ii) you want to explore a large region of the
available parameter space ( large here means more than you want to do by hand
but probably less than millions say).
Its tasks are
 - generate json input files from given python dictioniaries and assign unique
   filenames
 - call the user provided executable on the input files to create the
   corresponding output file
 - select existing output files from the data folder based on a given input
 - display all input parameters for which output data exists in the folder

### A first example

Here is an example of how to use the module

```python
import json
import simplesimdb
import yaml

db = simplesimdb.Manager(
    directory = 'ds_data', # where to store the generated data
    filetype='yaml', # file-ending of the output files
    executable='./execute.sh' # the program to execute to generate data
) 

# Let us generate an inputfile for our simulation
inputfile = { "n": 3, "Nx" : 20, "Ny" : 20, "Nz" : 20,
              "mx" : 10, "my" : 10 }

# run a simulation with the specified input
outfile = db.create( inputfile)
# now open and read the created output
with open( outfile) as f:
    output = yaml.full_load(f)
    print (json.dumps(output, indent=4))

# list all existing inputfiles in the directory
content = db.table() 
# the list of inputfiles is searchable:
found = list( filter( lambda entry : ( entry["mx"] == 10), content) )
# select a simulation if it exists
outfile = db.select( found[0]) 
# delete all generated data in directory and the directory itself
db.delete_all() 
```
where `execute.sh` is an executable that takes `directory/hashid.json` as input and creates the file `directory/hashid.yaml`
In this example `execute.sh` parses the json input into command line arguments to a Feltor code and redirect its output into the yaml file.

```bash
#!/bin/bash

: ${FELTOR_PATH:="../feltor"}

# Feltor's ds_t requires input parameters from the command line
# so we parse the json string using jq
cat $1 | jq '.n, .Nx, .Ny, .Nz, .mx, .my' | $FELTOR_PATH/inc/geometries/ds_t > $2
```

### Running on a cluster

In many cases simulations are too expensive to run on a local machine. In this case it is mandatory that simulations run on a cluster. The data could then be transfered back to  a local machine where the data exploration with for example a jupyter notebook takes place. With simplesimdb the recommended way of achieving this scenario is: 

(i) a `generate_data.py` file on the cluster

```python
import json
import simplesimdb as simplesim

m = simplesim.Manager( directory='data', executable='./execute.sh', filetype='nc')

inputfile = generate_input(  ... )
m.create(inputfile)
```

(ii) the `execute.sh` script in this case has to submit the jobs to the job queue (here with slurm):

```bash
#!/bin/bash

INFILE=$1

FILE="${INFILE%.*}"
HASHID=$(basename -- "$INFILE")
HASHID="${HASHID%.*}"

sbatch -o ${FILE}.out -e ${FILE}.err -J $HASHID  submit.sh $1 $2
```

(iii) the `submit.sh` script is a template job script for all simulations

```bash
#!/bin/bash

#SBATCH -N 1 -n 1 --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --partition=m100_fua_prod
#SBATCH --account=xxxxx_xxxxx
#SBATCH --time=8:00:00

echo 'Marconi 100 cluster with Tesla V100 GPUs'
: ${FELTOR_PATH:="../feltor"}

$FELTOR_PATH/src/reco2D/reconnection_hpc $1 $2
```

There are a few caveats to this workflow:

- simplesimdb has no way of knowing when a simulation is pending, running, finished or produced an error. The execute.sh returns if the job is successfully submitted
- in this example all jobs run on exactly the same hardware resources since all use the same job template submit script. 

### Restarting simulations

Sometimes simulation outputs cannot be created in a single run (due to file size, time limitations, etc.) but rather a simulation is partitioned (in time) into a sequential number of separate smaller runs. Correspondingly each run sequentially generates and stores only a partition of the entire output file. Each run restarts the simulation with the result of the previous run. The Manager solves this problem via the optional
simulation number n in its member functions. For n>0 create will pass the result of the previous simulation as a third input to the executable

See the following example to see how to create and subsequently iterate through restarted simulations

```python
import json
import simplesimdb as simplesim

m = simplesim.Manager( directory='data', executable='./execute.sh', filetype='txt')
# delete content of previous simulation run
m.delete_all()
# !!! after delete_all() we must reset the directory: !!!
m.directory = 'data'
 
inputfile1 = { "Hello" : "World"}
inputfile2 = { "Hello" : "User"}
# generate 3 data files for each input:
for n in range( 0,3) :
    m.create( inputfile1, n)
    m.create( inputfile2, n)

# Now search for a specific input file in the content
content = m.table()
found = list( filter( lambda entry : ( entry["Hello"] == "User"), content) )
print( found[0])
# Count all corresponding simulations
number = m.count( found[0])
print( "Number of simulations found:", number)
# and finally loop over and read each of the found simulations
for n in range( 0, number):
    f = open( m.outfile( found[0], n), "r")
    print ( "Contents of file", n )
    print ( f.read())
```

The `execute.sh` script in our example does not do much

```bash
#!/bin/bash

if [ $# -eq 2 ] # note the whitespaces
then
    # do something for first simulation
    echo $1 $2 > $2
else
    # do something else for restart
    echo "!!!!!RESTART!!!!!" > $2
    cat $3 >> $2
fi
```

## Current limitations

- Cannot manage simulations with more than one input file
  (probably the easiest solution is to concatenate the two files)
- Cannot manage simulations with more than one output file
- Cannot manage existing simulation files that do not have names assigned by the module (create View)
- Not optimized for (very) large input files: for Mega or Giga bytes say it
  is probably slow

## Why not just use an existing database management software like SQL

 - Relational databases are notoriously unsuited for scientific simulations so
   SQL is mostly not an option in the scientific community (in python we would
   use pandas anyway)
 - Search methods that DBMS offer are offered by python for dictionaries as
   well (especially if they are converted to tables in pandas)
 - There is an additional overhead of setting up and running a databaser server
 - When doing a parameter study you do not deal with millions of entries but a
   only a few hundred at best so a DBMS might just be overkill
 - There are NoSQL database managers like for example a document (json) manager
   like MongoDB that can  manage large files (videos, images, PDFs, etc.) along
   with supporting information (metadata) that fits naturally into JSON
   documents, but
 - Netcdf (or other output) files do not really map nicely into the mongodb
   data model since files larger than 16 MB require another FileGS server to be
   run
 - If netcdf files are stored by the DB manager how do we get access to it
   through other external programs like for example paraview?
 - If json files are hidden by the database manager how do we use them as input
   to run an executable to generate the output file?

## Contributions

Contributions are welcome.
## Authors

Matthias Wiesenberger

