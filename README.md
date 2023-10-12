# lanman2023
Code and data for the LANMAN 2023 paper "CUBIC Local Loss Recovery vs. BBR on (Satellite) Internet Paths"

`J. Deutschmann, K. -S. Hielscher and R. German, "CUBIC Local Loss Recovery vs. BBR on (Satellite) Internet Paths," 2023 IEEE 29th International Symposium on Local and Metropolitan Area Networks (LANMAN), London, United Kingdom, 2023, pp. 1-3, doi: 10.1109/LANMAN58293.2023.10189417.`

## Prepare Docker image
`sudo docker build -t llr .`

For other software requirements please check `run.py` and `plot.py`

## Run one experiment (must be run multiple times for more iterations)
`sudo python3 run.py --runDelayLoss --runDelayLinkrate`

## Plot results
`python3 plot.py --csvFiles *delayLoss.csv --plotDelayLoss`

`python3 plot.py --csvFiles *delayLinkrate.csv --plotDelayLinkrate`
