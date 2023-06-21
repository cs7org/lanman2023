import argparse
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import subprocess


setups = [{'llr': False, 'cc': "cubic", 'text': "CUBIC, no local loss recovery"},
          {'llr': True,  'cc': "cubic", 'text': "CUBIC, with local loss recovery"},
          {'llr': False, 'cc': "bbr",   'text': "BBR, no local loss recovery"}]


def beautifyDf(df):
    df = df.fillna(0)
    df['rate'] = df['rate'].astype(int)
    df['delay'] = df['delay'].astype(int)
    df['loss'] = df['loss'].astype(int)
    df['goodput'] /= 1e6
    df['goodputMedian'] /= 1e6
    df['goodputMedianNorm'] = df['goodputMedian'] / df['rate']  # normalize
    return df


def plotDelayLoss(csvInputFile):
    df = pd.read_csv(csvInputFile)
    df = beautifyDf(df)

    fig, axes = plt.subplots(1, 3, figsize=(12, 2.5))
    cbar_ax = fig.add_axes([.91, .28, .02, .6])  # left, bottom, width, height

    for idxSetup, setup in enumerate(setups):
        llr = setup['llr']
        cc = setup['cc']
        text = setup['text']

        delayValueFilter = "(delay == 10 or delay == 50 or delay == 100 or delay == 300)"

        df_temp = df.query('load == "time60" & llr == @llr & cc == @cc & ' + delayValueFilter).pivot("loss", "delay", "goodputMedian")
        sns.heatmap(df_temp, ax=axes[idxSetup], annot=True, vmin=0, vmax=10, cmap="Oranges", fmt=".1f",
                    cbar=(idxSetup == 0), cbar_ax=cbar_ax if idxSetup == 0 else None) \
            .set_title(text)

        axes[idxSetup].set(xlabel='One-way delay [ms]\n', ylabel='Packet loss rate [%]')

    cbar_ax.set_ylabel("Goodput [Mbit/s]")
    fig.tight_layout(rect=[0, 0, .9, 1])

    outFilename = "DelayLoss.pdf"
    plt.rcParams['pdf.fonttype'] = 42
    plt.savefig(outFilename)
    subprocess.run(f"pdfcrop {outFilename} && rm {outFilename}", shell=True)


def plotDelayLinkrate(csvInputFile):
    df = pd.read_csv(csvInputFile)
    df = beautifyDf(df)

    fig, axes = plt.subplots(1, 3, figsize=(12, 2.5))
    cbar_ax = fig.add_axes([.91, .28, .02, .6])  # left, bottom, width, height

    for idxSetup, setup in enumerate(setups):
        llr = setup['llr']
        cc = setup['cc']
        text = setup['text']

        df_temp = df.query('load == "time60" & llr == @llr & cc == @cc & loss == 1').pivot("rate", "delay", "goodputMedianNorm")
        sns.heatmap(df_temp, ax=axes[idxSetup], annot=True, vmin=0, vmax=1, cmap="Oranges", fmt=".2f",
                    cbar=(idxSetup == 0), cbar_ax=cbar_ax if idxSetup == 0 else None) \
            .set_title(text)

        axes[idxSetup].set(xlabel='One-way delay [ms]\n', ylabel='Link rate [Mbit/s]')

    cbar_ax.set_ylabel("Goodput / Link rate")
    fig.tight_layout(rect=[0, 0, .9, 1])

    outFilename = "DelayLinkrate.pdf"
    plt.rcParams['pdf.fonttype'] = 42
    plt.savefig(outFilename)
    subprocess.run(f"pdfcrop {outFilename} && rm {outFilename}", shell=True)


def mergeCsvFiles(csvFileList):
    df_list = [pd.read_csv(csvFile, index_col=0) for csvFile in csvFileList]
    df_list = [df.set_index(['llr', 'cc', 'load', 'rate', 'delay', 'loss']) for df in df_list]

    # https://stackoverflow.com/questions/41815079/pandas-merge-join-two-data-frames-on-multiple-columns
    # https://stackoverflow.com/questions/23668427/pandas-three-way-joining-multiple-dataframes-on-columns
    df_concat = pd.concat(df_list, axis=1, join='outer')  # df then has multiple timeInterval and goodput columns
    df_concat = df_concat.drop(columns=['timeInterval'])

    df_concat['goodputMedian'] = df_concat['goodput'].median(axis=1)
    df_concat = df_concat.astype({'goodputMedian': 'int'})

    df_concat.to_csv("mergedFiles.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--csvFiles", nargs='+', help="List of CSV files to be merged")
    parser.add_argument("--plotDelayLoss", action='store_true')
    parser.add_argument("--plotDelayLinkrate", action='store_true')
    args = parser.parse_args()
    print(args)

    if args.csvFiles:
        mergeCsvFiles(args.csvFiles)

    if args.plotDelayLoss:
        plotDelayLoss("mergedFiles.csv")

    if args.plotDelayLinkrate:
        plotDelayLinkrate("mergedFiles.csv")


