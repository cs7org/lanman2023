# lanman2023
Code and data for the LANMAN 2023 paper "CUBIC Local Loss Recovery vs. BBR on (Satellite) Internet Paths"

## Prepare Docker image
`sudo docker build -t llr .`

For other software requirements please check `run.py` and `plot.py`

## Run one experiment (must be run multiple times for more iterations)
`sudo python3 run.py --runDelayLoss --runDelayLinkrate`

## Plot results
`python3 plot.py --csvFiles *delayLoss.csv --plotDelayLoss`

`python3 plot.py --csvFiles *delayLinkrate.csv --plotDelayLinkrate`
