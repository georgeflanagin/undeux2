#!/bin/bash -e

#SBATCH --job-name=undeux
#SBATCH --output=undeux.%j.out
#SBATCH --ntasks=1
#SBATCH --time=0:10:00
#SBATCH --mail-type=ALL
#SBATCH --mem=2GB
#SBATCH --partition=erickson
#SBATCH --cpus-per-task=3

# Print the simulation start date/time
date

# Print the node the simulation is running on
echo "I ran on:"
echo "SLURM_NODELIST=$SLURM_NODELIST"

# Return the context/PWD to the directory where *this* file is located.
cd $SLURM_SUBMIT_DIR

cd $HOME/undeux2
export PYTHONPATH=/usr/local/sw/hpclib

export SCRATCH=/localscratch/installer

mkdir -p $SCRATCH
sqlite3 $SCRATCH/undeux.db < undeux.sql
sleep 1
touch undeux.py
python undeux.py -y --db $SCRATCH/undeux.db --dir /scratch/installer 



# Print the simulation end date/time
date

