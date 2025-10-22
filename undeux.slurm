#!/bin/bash -e

#SBATCH --job-name=undeux
#SBATCH --output=undeux.%j.out
#SBATCH --ntasks=1
#SBATCH --time=24:00:00
#SBATCH --mail-type=ALL
#SBATCH --mail-user=gflanagi@richmond.edu
#SBATCH --mem=12GB
#SBATCH --partition=bukach
#SBATCH --cpus-per-task=4


# Print the simulation start date/time
date

# Print the node the simulation is running on
echo "I ran on:"
echo "SLURM_NODELIST=$SLURM_NODELIST"

export PYTHON=/usr/local/sw/anaconda/anaconda3/bin/python
export PYTHONPATH=/usr/local/sw/hpclib
export SCRATCH=/localscratch/installer
export TARGET=/scratch/cparish
export UNDEUXDIR=/usr/local/sw/undeux2
export PYTHONPATH="$UNDEUXDIR:$PYTHONPATH"

# Make sure we have a directory.
mkdir -p "$SCRATCH"
cd "$SCRATCH"

# Go for it.
/usr/bin/time -v "$PYTHON" "$UNDEUXDIR/undeux.py" -z "$TARGET" 

# Bring the file back
dd if=$DB of=$HOME/undeux.db bs=1M
rm -f "$DB"

# Print the simulation end date/time
date

