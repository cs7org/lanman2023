import argparse
import os
import subprocess
import time
from datetime import datetime
import pandas as pd
import json


# TODO setCc requires sysctl without sudo password
def setCc(cc):
    assert cc == "cubic" or cc == "bbr", "Specify cubic or bbr"

    print("Current sysctl settings:")
    subprocess.run("sysctl net.core.default_qdisc".split())
    subprocess.run("sysctl net.ipv4.tcp_congestion_control".split())

    if cc == "cubic":
        subprocess.run("sudo sysctl -w net.core.default_qdisc=fq_codel".split())
        subprocess.run("sudo sysctl -w net.ipv4.tcp_congestion_control=cubic".split())
    elif cc == "bbr":
        subprocess.run("sudo sysctl -w net.core.default_qdisc=fq".split())
        subprocess.run("sudo sysctl -w net.ipv4.tcp_congestion_control=bbr".split())


def startOpenvpn():
    subprocess.run("docker exec llr-gateway openvpn --config config/server.ovpn --daemon".split())
    subprocess.run("docker exec llr-client openvpn --config config/client.ovpn --daemon".split())
    time.sleep(3)
    subprocess.run("docker exec llr-client ip r".split())


# TODO netem link parameters are set symmetrical
def setNetem(container, rateMbps: int = None, delayMs: int = None, lossPercent: int = None):
    print("setNetem")
    assert container == "wlan" or container == "sat", "Specify wlan or sat container"

    #remove old tc (no check=True in case there was no tc before)
    subprocess.run(f"docker exec llr-netem-{container} tc qdisc del dev {container}left0 root".split())
    subprocess.run(f"docker exec llr-netem-{container} tc qdisc del dev {container}right0 root".split())

    if rateMbps is None and delayMs is None and lossPercent is None:
        print(f"removed tc from llr-netem-{container} without adding new tc")
        return

    for side in ["left", "right"]:
        cmd=f"docker exec llr-netem-{container} tc qdisc add dev {container}{side}0 root handle 1:0 netem"
        if rateMbps:
            cmd += f" rate {rateMbps}Mbit"
        if delayMs:
            cmd += f" delay {delayMs}ms"
        if lossPercent:
            cmd += f" loss {lossPercent}%"
        print(cmd)
        subprocess.run(cmd.split(), check=True)


def runDockerCompose(openvpn: bool, cc, setup, res_dict):
    s = setup

    setCc(cc)

    try:
        os.remove("output/client_ready")
    except OSError:
        pass

    subprocess.Popen("docker-compose up --remove-orphans --force-recreate".split())

    while not os.path.isfile("output/client_ready"):
        print("waiting until client is ready (check file output/client_ready)")
        time.sleep(1)
    os.remove("output/client_ready")

    if openvpn:
        startOpenvpn()

    for load in s['loads']:
        loadString = load.replace(" ", "")
        for rate in s['rates']:
            for delay in s['delays']:
                for loss in s['plrs']:
                    outfilePrefix = f"iperf_openvpn{openvpn}_cc{cc}_load{loadString}_rate{rate}_delay{delay}_loss{loss}"
                    print(f"\n\n\nRunning setup: {outfilePrefix}")

                    setNetem("wlan", rateMbps=1000, lossPercent=loss)
                    setNetem("sat", rateMbps=rate, delayMs=delay)

                    cmd = f"docker exec llr-server iperf -s -i1 --enhanced --reportstyle C" \
                          f" --output output/{outfilePrefix}_serverTx.csv"
                    print(cmd)
                    subprocess.Popen(cmd.split())
                    time.sleep(1)

                    cmd = f"docker exec llr-client iperf -c 10.0.3.3 -i1 --enhanced --reportstyle C" \
                          f" --reverse --{load}" \
                          f" --output output/{outfilePrefix}_clientRx.csv"
                    print(cmd)
                    subprocess.run(cmd.split())
                    time.sleep(1)

                    print("kill iperf server")
                    subprocess.run("docker exec llr-server pkill iperf".split())  # subprocess.kill() does not kill server
                    while subprocess.run("docker exec llr-server netstat -tlpn |grep iperf", shell=True).returncode == 0:
                        print("iperf server still running...")
                        time.sleep(1)

                    #Eval
                    #iperf csv header https://sourceforge.net/p/iperf2/code/ci/master/tree/src/ReportOutputs.c#l1385
                    csvRxHeader = ["date", "destIp", "destPort", "srcIp", "srcPort", "transferID",
                                   "timeInterval", "bytes", "goodput",
                                   "readCnt", "read0", "read1", "read2", "read3", "read4", "read5", "read6", "read7"]
                    dfCsvRx = pd.read_csv(f"output/{outfilePrefix}_clientRx.csv",
                                          header=None, names=csvRxHeader)
                    res_dict['llr'].append(openvpn)
                    res_dict['cc'].append(cc)
                    res_dict['load'].append(loadString)
                    res_dict['rate'].append(rate)
                    res_dict['delay'].append(delay)
                    res_dict['loss'].append(loss)
                    res_dict['timeInterval'].append(list(dfCsvRx['timeInterval'])[-1])
                    res_dict['goodput'].append(list(dfCsvRx['goodput'])[-1])
                    #print(res_dict)

    subprocess.run("docker-compose down".split())


def runSetup(setup):
    res_dict = {'llr': [],
                'cc': [],
                'load': [],
                'rate': [],
                'delay': [],
                'loss': [],
                'timeInterval': [],
                'goodput': []}

    for openvpn in setup['openvpn']:
        for cc in setup['cc']:
            runDockerCompose(openvpn=openvpn, cc=cc, setup=setup, res_dict=res_dict)

    os.mkdir(f"{setup['name']}")
    subprocess.run(f"mv output/iperf_*.csv {setup['name']}", shell=True)

    with open(f"{setup['name']}.json", "w") as outfile:
        json.dump(setup, outfile, indent=2)

    pd.DataFrame(res_dict).to_csv(f"{setup['name']}.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--runDelayLoss", action='store_true')
    parser.add_argument("--runDelayLinkrate", action='store_true')
    args = parser.parse_args()
    print(args)

    currDatetime = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.runDelayLoss:
        setup = {'name': f"{currDatetime}_delayLoss",
                 'description': "vary loss and delay, rate is 10",
                 'openvpn': [False, True],
                 'cc': ["cubic", "bbr"],
                 'loads': ["time 60"],  #"time 10"
                 'rates': [10],
                 'delays': [10, 50, 100, 300],  #None, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300
                 'plrs': [None, 1, 2, 3, 4]
                 }
        runSetup(setup)

    if args.runDelayLinkrate:
        setup = {'name': f"{currDatetime}_delayLinkrate",
                 'description': "vary link rate and delay, loss is 0 or 1",
                 'openvpn': [False, True],
                 'cc': ["cubic", "bbr"],
                 'loads': ["time 60"],  #"num 1M", "num 10M"
                 'rates': [1, 10, 50, 100],
                 'delays': [10, 50, 100, 300],
                 'plrs': [1]  #None
                 }
        runSetup(setup)

