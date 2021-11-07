# EECS545

# Requirements

Use the environment.yml to find the associated packages and versions. 

# Datasets 

Example data loaders can be found in data_loader_example.py 

Can be run by passing in an argument denoting the data set to load, such as data_loader_example.py -dataset credit

# Models

Folder models holds the various architectures. Examples to load, train, and evaluate can be found in run_models.py. Run_models.py has a lot of possible arguments, here as an example to run:

python run_models.py --dropout 0.5 --hidden 16 --lr 1e-3 --epochs 1000 --model gcn --dataset german --seed 1

where --model can be ['gcn', 'sage'] and --dataset can be ['german', 'credit', 'bail'] 

model weights are saved to weights folder and evaluation metricss are saved to results. 


