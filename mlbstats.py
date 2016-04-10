___author___ = "Jason McGinthy"

from bs4 import BeautifulSoup
from operator import itemgetter

import requests
import csv
import time
import datetime
import re


def main():
    past_stats = read_in_past_stats()
    top = statsscraper()
    stats, past_stats = parse_stats(top,past_stats)
    #player_stats = calc_odds(stats)
    write_out_csv(stats)
    write_out_csv(past_stats)


def get_http(url):
    r = requests.get(url)
    data = r.text
    return BeautifulSoup(data)


def parse_stats(Top, past_stats):
    Stats = []
    TrainingSet = []
    days = re.compile("Sun|Mon|Tue|Wed|Thu|Fri|Sat")
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(1)
    today = today.strftime("%a")
    yesterday = yesterday.strftime("%a")

    for i in range(len(Top)):
    # for i in range(len(Top)):
        Name = (Top[i]).split('/')[-1]
        idx = 0
        omit = False
        past_omit = False
        SeasonAvg = 0
        LSDAvg = 0
        vsAvg = 0
        ABs = 0
        walks = 0
        CareerAvg = 0
        Hit = ""

        soup = get_http((Top[i]))

        Team = soup.find('h6').text

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

            if (len(tds)) == 17:  # first row with length 17 hold current season stats
                if "2016 Regular Season" in tds[0].find(text=True):
                    SeasonAvg = float(tds[-4].find(text=True))
                    walks = int(tds[-8].find(text=True))
                if "Career" in tds[0].find(text=True):
                    CareerAvg = float(tds[-4].find(text=True))

            if (len(tds)) == 14 and tr.text[0:4] != 'DATE':
                #Date = str(tds[0].text)
                names = [item[0] for item in past_stats]
                try:
                    idx = names.index(Name)
                    Hit = int(tds[5].text)
                except ValueError:
                    past_omit = True

                break

        if not omit:
            Stats.append([Name, Team, CareerAvg, SeasonAvg, LSDAvg, vsAvg, ABs, walks])  # appends player and stats to list

        if not past_omit:
            past_stats[idx].append(Hit)

    return Stats, past_stats

def calc_odds(Stats):
    Player_Odds = []
    weightedTotal = 0

    max_avg = max(max([p[2]]) for p in Stats)
    max_lsd = max(max([p[3]]) for p in Stats)
    max_cmu = max(max([p[4]]) for p in Stats if p[5] >= 5)
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


def write_out_csv(stats):
    #Print stats to CSV file
    #timestamp = datetime.datetime.now()
    if len(stats[0]) == 8:
        filename = "current_stats.csv"
    else:
        filename = "past_stats.csv"

    with open(filename, "wt") as f:
        if filename is "current_stats.csv":
            writer = csv.DictWriter(f, lineterminator='\n',
                                fieldnames = ["Name", "Team", "Career Avg",
                                              "Season Avg", "LSD Avg", "CMU Avg", "MU ABs", "Walks"])
        else:
            writer = csv.DictWriter(f, lineterminator='\n',
                                fieldnames = ["Name", "Team", "Career Avg",
                                              "Season Avg", "LSD Avg", "CMU Avg", "MU ABs", "Walks", "Hits"])
        writer.writeheader()
        writer = csv.writer(f, lineterminator='\n')
        writer.writerows(stats)

def read_in_past_stats():
    with open('past_stats.csv', 'rt') as f:
        next(f)
        reader = csv.reader(f)
        past_stats = list(reader)

    #print(past_stats)
    return past_stats


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