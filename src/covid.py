from pyjstat import pyjstat
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from matplotlib.ticker import ScalarFormatter
import requests
import pytz
from pandas.plotting import register_matplotlib_converters
from ruamel.yaml import YAML
register_matplotlib_converters()

fi_tz = pytz.timezone("Europe/Helsinki")

annotations = [
    (datetime.datetime(2020,3,18, tzinfo=fi_tz), "Poikkeustila voimaan"),
    (datetime.datetime(2020,5,14, tzinfo=fi_tz), "Takaisin kouluun"),
    (datetime.datetime(2020,10,2, tzinfo=fi_tz), "Kasvomaskisuositus"),
    (datetime.datetime(2020,10,15, tzinfo=fi_tz), "Uudet suositukset"),
    (datetime.datetime(2020,11,19, tzinfo=fi_tz), "HUS leviämisv."),
    (datetime.datetime(2020,11,30, tzinfo=fi_tz), "HUS uudet rajoitukset"),
    (datetime.datetime(2021,3,1, tzinfo=fi_tz), "Ravintolarajoitukset"),
    # (datetime.date(2021,3,8), "Poikkeustila 2"),
    (datetime.datetime(2021,4,18, tzinfo=fi_tz), "Ravintolat auki"),
    (datetime.datetime(2021,4,29, tzinfo=fi_tz), "Kuntosalit auki"),
]

annotations_infected = [
#    (datetime.date(2020,11,14), "Vikat koiradojotreenit :("),
]

infected_url = "https://w3qa5ydb4l.execute-api.eu-west-1.amazonaws.com/prod/processedThlData"

def get_data(shp):
    resp = requests.get(infected_url)
    if resp.status_code != 200:
        raise Exception(f"Data loading failed {resp.status_code}")
    data_json = resp.json()

    dates = [(r["date"], r["value"]) for r in data_json["confirmed"][shp]]
    infected = pd.DataFrame([r[1] for r in dates], index = pd.to_datetime([r[0] for r in dates]), columns=["infected"])
    for n in range(0, infected.shape[0]-7):
        infected.loc[infected.index[n+7], "infected_last_week"] = infected.iloc[n,0]
    for n in range(0, infected.shape[0]-7):
        sum = 0
        for i in range(7):
            sum += infected.iloc[n+i,0]
        infected.loc[infected.index[n+7], "infected_sum_last_week"] = sum
    for n in range(0, infected.shape[0]-7):
        infected.loc[infected.index[n+7], "infected_sum_previous_week"] = infected.iloc[n,2]
    infected["weekly_change"] = infected["infected_sum_last_week"] / infected["infected_sum_previous_week"]
    return infected

def add_vline(ax, x, label, column):
    x_bounds = ax.get_xlim()
    ax.axvline(x=x, ymin=0, ymax=1)
    ax.annotate(s='label', xy =(((x-x_bounds[0])/(x_bounds[1]-x_bounds[0])),1.01), xycoords='axes fraction', verticalalignment='right', horizontalalignment='right bottom' , rotation = 270)

def get_fwd_range(data, start_index, max_items, column):
    fwd_data = data.loc[start_index:]
    row_count = fwd_data.shape[0]
    if row_count > max_items:
        fwd_data = fwd_data[:max_items]
    return (fwd_data[column].min(), fwd_data[column].max())

_default_start = fi_tz.localize(datetime.datetime(2020,3,1, 12, 0, 0))

def plot_history(shp, start_date=_default_start, end_date=None):
    if not end_date:
        end_date = fi_tz.localize(datetime.datetime.now()) - datetime.timedelta(days=3)
    fi_data = get_data(shp)
    fig, ax = plt.subplots(2,1,figsize=(12,12))
    ax[0].set_xlim(start_date, end_date)
    ax[0].plot(fi_data["weekly_change"])
    #ax[0].vlines(datetime.date(2020,3,18), 0, 14, color='green')
    #add_vline(ax[0], datetime.date(2020,3,18), "Poikkeustila")
    for d, ann in annotations:
        if d >= start_date and d <= end_date:
            try:
                yval = fi_data.loc[str(d)]["weekly_change"][0]

                # Determine where to put the label
                ymin, ymax = get_fwd_range(fi_data, d, 30, "weekly_change")
                dy = 15
                if yval - ymin < ymax-yval:
                    # Future data is mostly above current Y value so put label below it
                    dy = -15

                if not np.isfinite(yval):
                    yval = 0.3
                ax[0].annotate(ann, (d, yval), xytext=(0, dy),
                        textcoords='offset points', arrowprops=dict(arrowstyle='-|>'))
            except Exception as e:
                pass

    ax[0].set_ylim(0.3,14)
    ax[0].set_yscale("log", base=2)
    ax[0].yaxis.set_major_formatter(ScalarFormatter())
    ax[0].set_ylabel("Tartunamäärän suhteellinen muutos viikossa")
    ax[0].hlines(1, start_date, end_date, color='red')
    ax[0].hlines(2, start_date, end_date, color='gray')
    ax[0].hlines(1.4, start_date, end_date, color='gray')

    ax[1].plot(fi_data["infected_sum_last_week"])
    ax[1].set_xlim(start_date, end_date)
    ax[1].set_yscale("log", base=10)
    ax[1].yaxis.set_major_formatter(ScalarFormatter())
    ax[1].set_ylabel("Tartuntoja viikossa")

    for d, ann in annotations_infected:
        if d >= start_date and d <= end_date:
            try:
                yval = fi_data.loc[str(d)]["infected_sum_last_week"][0]
                if not np.isfinite(yval):
                    yval = 0.3
                ax[1].annotate(ann, (d, yval), xytext=(0, 15),
                        textcoords='offset points', arrowprops=dict(arrowstyle='-|>'))
            except Exception as e:
                pass


    # Draw current level
    current = fi_data.iloc[[fi_data.index.get_indexer([end_date], method='nearest')][0]]["infected_sum_last_week"]
    ax[1].hlines(current, start_date, end_date, color="lightgray")

    ax[0].set_facecolor("white")
    ax[1].set_facecolor("white")
    fig.suptitle(f"COVID, {shp}")
    fig.set_facecolor("white")
