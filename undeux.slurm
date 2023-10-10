#!/bin/bash -e

#SBATCH --job-name=undeux
#SBATCH --output=undeux.%j.out
#SBATCH --ntasks=1
#SBATCH --time=1:00:00
#SBATCH --mail-type=ALL
#SBATCH --mail-user=hpc@richmond.edu
#SBATCH --mem=4GB
#SBATCH --partition=erickson
#SBATCH --cpus-per-task=3


# Print the simulation start date/time
date

# Print the node the simulation is running on
echo "I ran on:"
echo "SLURM_NODELIST=$SLURM_NODELIST"

export PYTHON=/usr/local/sw/anaconda/anaconda3/bin/python
export PYTHONPATH=/usr/local/sw/hpclib
export SCRATCH=/localscratch/installer
export DB=$SCRATCH/undeux.db
export TARGET=/scratch/installer
export UNDEUXDIR=/usr/local/sw/undeux2

# This is our home.
cd "$UNDEUXDIR"

# Make sure we have a directory.
mkdir -p "$SCRATCH"

# Build the database
rm -f "$DB"
sqlite3 "$DB" < undeux.sql

# Wait one second so that the program doesn't think
# the database is newer than it is.
sleep 1
touch undeux.py

# Go for it.
/usr/bin/time "$PYTHON" undeux.py -y --db "$DB" --dir "$TARGET"

# Bring the file back
dd if=$DB of=$HOME/undeux.db bs=1M
rm -f "$DB"

# Print the simulation end date/time
date

