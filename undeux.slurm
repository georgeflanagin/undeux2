#!/bin/bash -e

#SBATCH --job-name=undeux
#SBATCH --output=undeux.%j.out
#SBATCH --ntasks=1
#SBATCH --time=0:10:00
#SBATCH --mail-type=ALL
#SBATCH --mem=20GB
#SBATCH --partition=all
#SBATCH --cpus-per-task=3

# Print the simulation start date/time
date



# Print the node the simulation is running on
echo "I ran on:"
echo "SLURM_NODELIST=$SLURM_NODELIST"

# Return the context/PWD to the directory where *this* file is located.
cd $SLURM_SUBMIT_DIR

cd /usr/local/sw/undeux
python undeux.py -y --db undeux.db --dir /scratch/installer 


# Print the simulation end date/time
date

