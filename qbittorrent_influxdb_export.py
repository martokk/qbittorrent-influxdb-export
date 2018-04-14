#!/usr/bin/python

import time
import argparse # for arg parsing...
import json # for parsing json
import requests
from requests.auth import HTTPDigestAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from multiprocessing import Process
from datetime import datetime # for obtaining the curren time and formatting it
from influxdb import InfluxDBClient # via apt-get install python-influxdb
requests.packages.urllib3.disable_warnings(InsecureRequestWarning) # suppress unverified cert warnings

url_format = '{0}://{1}:{2}/'

def main():
    args = parse_args()
    url = get_url(args.qbittorrentwebprotocol, args.qbittorrenthost, args.qbittorrentport)
    influxdb_client = InfluxDBClient(args.influxdbhost, args.influxdbport, args.influxdbuser, args.influxdbpassword, args.influxdbdatabase)
    create_database(influxdb_client, args.influxdbdatabase)
    init_exporting(args.interval, url, influxdb_client)

def parse_args():
    parser = argparse.ArgumentParser(description='Export qBittorrent data to influxdb')
    parser.add_argument('--interval', type=int, required=False, default=5, help='Interval of export in seconds')
    parser.add_argument('--qbittorrentwebprotocol', type=str, required=False, default="http", help='qBittorrent web protocol (http)')
    parser.add_argument('--qbittorrenthost', type=str, required=False, default="localhost", help='qBittorrent host (test.com))')
    parser.add_argument('--qbittorrentport', type=int, required=False, default=8080, help='qBittorrent port')
    parser.add_argument('--qbittorrentuser', type=str, required=False, default="", help='qBittorrent user')
    parser.add_argument('--qbittorrentpassword', type=str, required=False, default="", help='qBittorrent password')
    parser.add_argument('--influxdbhost', type=str, required=False, default="localhost", help='InfluxDB host')
    parser.add_argument('--influxdbport', type=int, required=False, default=8086, help='InfluxDB port')
    parser.add_argument('--influxdbuser', type=str, required=False, default="", help='InfluxDB user')
    parser.add_argument('--influxdbpassword', type=str, required=False, default="", help='InfluxDB password')
    parser.add_argument('--influxdbdatabase', type=str, required=False, default="qbittorrent", help='InfluxDB database')
    return parser.parse_args()

def transfer_info(url,influxdb_client):
    args = parse_args()
    try:
        data = requests.get('{0}{1}'.format(url, 'query/transferInfo'), verify=False, timeout=8, auth=HTTPDigestAuth(args.qbittorrentuser, args.qbittorrentpassword)).json()

        if data:
            dl_speed = float(data['dl_info_speed'])
            up_speed = float(data['up_info_speed'])
            status = data['connection_status']

            json_body = [
            {
                "measurement": "transfer_info",
                "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                "fields" : {
                    "dl_speed": dl_speed,
                    "up_speed": up_speed,
                    "status": status
                }
            }]
            influxdb_client.write_points(json_body)

    except Exception as e:
        print str(e)
        pass

def torrent_data(url,influxdb_client):
    args = parse_args()
    try:
        data = requests.get('{0}{1}'.format(url, 'query/torrents?filter=downloading'), verify=False, timeout=8, auth=HTTPDigestAuth(args.qbittorrentuser, args.qbittorrentpassword)).json()

        if data:
            total = long(len(data))


            json_body = [
                {
                    "measurement": "torrent_data",
                    "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "fields" : {
                        "total": total
                        }
                    }]
            influxdb_client.write_points(json_body)

    except Exception as e:
        print str(e)
        pass

def create_database(influxdb_client, database):
    try:
        influxdb_client.query('CREATE DATABASE {0}'.format(database))
    except Exception:
        pass

def init_exporting(interval, url, influxdb_client):
    while True:
        transferinfo = Process(target=transfer_info, args=(url,influxdb_client))
        transferinfo.start()

        torrentdata = Process(target=torrent_data, args=(url,influxdb_client))
        torrentdata.start()

        time.sleep(interval)

def get_url(protocol,host,port):
    return url_format.format(protocol,host,port)

if __name__ == '__main__':
    main()
