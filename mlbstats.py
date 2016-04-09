___author___ = "Jason McGinthy"

from bs4 import BeautifulSoup
from operator import itemgetter

import requests
import csv
import time
import datetime
import re


def main():
    top = statsscraper()
    stats = parse_stats(top)
    player_stats = calc_odds(stats)
    write_out_csv(player_stats)
    #read_in_stats()

def get_http(url):
    r = requests.get(url)
    data = r.text
    return BeautifulSoup(data)


def parse_stats(Top):
    Stats = []
    days = re.compile("Sun|Mon|Tue|Wed|Thu|Fri|Sat")
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(1)
    today = today.strftime("%a")
    yesterday = yesterday.strftime("%a")

    for i in range(len(Top)):
    # for i in range(len(Top)):
        omit = False
        SeasonAvg = 0
        LSDAvg = 0
        vsAvg = 0
        ABs = 0
        walks = 0
        CareerAvg = 0
        Hit = ""

        soup = get_http((Top[i]))

        for tr in soup.find_all('tr'):  # finds all rows
            tds = tr.find_all('td')  # finds all tds in each row
            timediv = tr.find_all("div", { "class" : "time" })


            if len(timediv) != 0:
                match = days.search(timediv[0].text)
                if match is not None and (timediv[0].text[match.start():match.end()] != today
                                        and timediv[0].text[match.start():match.end()] != yesterday):
                    omit = True
                    break

            if (len(tds)) == 10:  # rows with 10 tds have current splits

                if "Last seven days" in tds[0].find(text=True):  # Finds last seven days split
                    LSDAvg = float(tds[9].find(text=True))
                if "(Car.)" in tds[0].find(text=True):  # Finds if hitter has faced expected pitcher
                    vsAvg = float(tds[9].find(text=True))
                    ABs = int(tds[1].find(text=True))
                # if "This Game" in tds[0].find(text=True):
                #     if int(tds[3].find(text=True)) == 0 and int(tds[1].find(text=True)) != 0:
                #         Hit = 0
                #     elif int(tds[3].find(text=True)) == 0 and int(tds[1].find(text=True)) == 0:
                #         omit = True
                #     else:
                #         Hit = int(tds[3].find(text=True))

            if (len(tds)) == 17:  # first row with length 17 hold current season stats
                if "2016 Regular Season" in tds[0].find(text=True):
                    SeasonAvg = float(tds[-4].find(text=True))
                    walks = int(tds[-8].find(text=True))
                if "Career" in tds[0].find(text=True):
                    CareerAvg = float(tds[-4].find(text=True))

            if (len(tds)) == 14 and tr.text[0:4] != 'DATE':
                Date = str(tds[0].text)
                Hit = int(tds[5].text)
                break


        if not omit:
            Stats.append([(Top[i]).split('/')[-1], SeasonAvg, LSDAvg, vsAvg, ABs, Hit, walks, CareerAvg])  # appends player and stats to list

    return Stats

def calc_odds(Stats):
    Player_Odds = []
    weightedTotal = 0

    max_avg = max(max([p[1]]) for p in Stats)
    max_lsd = max(max([p[2]]) for p in Stats)
    max_cmu = max(max([p[3]]) for p in Stats if p[4] >= 5)
    max_walk = max(max([p[6]]) for p in Stats)
    max_career = max(max([p[7]]) for p in Stats)
    #max_vs_right_left
    #max_day_night

    for p in Stats:

        if p[3] != -1:
            # Changes weights based on how many ABs against starting pitcher
            weight_avg = .1

            if p[4] >= 20:
                weight_lsd = .15
                weight_cmu = .55
            elif p[4] >= 15:
                weight_lsd = .2
                weight_cmu = .5
            elif p[4] >= 10:
                weight_lsd = .25
                weight_cmu = .45
            elif p[4] >= 5:
                weight_lsd = .3
                weight_cmu = .4
            else:
                weight_lsd = .5
                weight_cmu = .2

        else:
            weight_avg = .3
            weight_lsd = .5
            weight_cmu = 0

        weight_walk = .05
        weight_career = .15

        weightedTotal = p[1] / max_avg * weight_avg + p[2] / max_lsd * weight_lsd + p[3] / max_cmu * weight_cmu \
                        + (1-p[6]/max_walk)*weight_walk + p[7]/max_career * weight_career

        Player_Odds.append([p[0], weightedTotal, p[5], "", "%.3f" % p[7], "%.3f" % p[1],"%.3f" % p[2],"%.3f" % p[3], p[4], p[6]])
                            #[Name, Weighted Odds, Hit or Not, Career Avg, Season Avg, LSD Avg, CMU Avg MU ABs, Walks]

    return (sorted(Player_Odds, key=itemgetter(1), reverse=True ))


def write_out_csv(Player_Odds):
    #Print stats to CSV file
    timestamp = datetime.datetime.now()
    filename = "stats_" + timestamp.strftime("%Y-%m-%d_%H%M") + ".csv"

    with open(filename, "wt") as f:
        writer = csv.DictWriter(f, lineterminator='\n',
                                fieldnames = ["Name", "Weighted Average", "Hit or Not", "", "Career Avg",
                                              "Season Avg", "LSD Avg", "CMU Avg", "MU ABs", "Walks"])
        writer.writeheader()
        writer = csv.writer(f, lineterminator='\n')
        writer.writerows(Player_Odds)

def read_in_stats():
    with open('statsoutput.csv', 'rt') as f:
        reader = csv.reader(f)
        stats = list(reader)

    print(stats)
    #return stats


def statsscraper():
    Top = []  # holds links for the Top 40 hitters

    urls = ["http://espn.go.com/mlb/stats/batting/_/count/1/qualified/true",
            "http://espn.go.com/mlb/stats/batting/_/count/41/qualified/true",
            "http://espn.go.com/mlb/stats/batting/_/count/81/qualified/true"]  # Top 1-120
    for url in urls:
        soup = get_http(url)

        for link in soup.find_all('a'):  # finds all links on the page
            if "mlb/player/_/id/" in link.get('href'):  # limits links to players' pages
                Top.append(link.get('href'))  # saves Top 120 hitters links

    return Top


######## Main Program ########
if __name__ == "__main__":
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))