#!/usr/bin/python3
import subprocess
import json
import requests
from config import influx_url, influx_token, influx_org, influx_bucket
import time
import os

# script for uploading disk tbw from samsung ssd's to influxdb
# currently functioning with the 850/860 PRO and 870 EVO
# Host: Proxmox VE
class Drive:
    def __init__(self, info):
        self.drive_letter = info
    def load_data(self):
        raw = subprocess.run(f"/usr/sbin/smartctl -a /dev/{self.drive_letter} -j", capture_output=True, shell=True)
        info = json.loads(raw.stdout.decode('utf-8'))
        for t in info["ata_smart_attributes"]["table"]:
            if t["id"] == 241:
                self.lba = t["raw"]["value"]
        self.model = info["model_name"].replace(" ", "\\ ")
        sector_size = 512
        self.tbw = round(self.lba * sector_size / (1024**4))
        self.time = int(time.time())
        self.node = os.uname()[1]
        

def influx_post_write_connector(content):
    url = f"{influx_url}:8086/api/v2/write?org={influx_org}&bucket={influx_bucket}&precision=s"
    headers = {"Authorization": f'Token {influx_token}', "Content-Type": "text/plain; charset=utf-8", "Accept": "application/json"}
    request = requests.post(url, headers=headers, data=content)
    return request.text

def get_blockdevices():
    process = subprocess.run("/usr/bin/lsblk --json -o NAME,MOUNTPOINT".split(), capture_output=True, text=True)
    blockdevices = json.loads(process.stdout)
    devices = []
    # list of devices to skip, add more as needed
    bad_devices = ["rbd0", "sr0","rbd1"]
    for device in blockdevices["blockdevices"]:
        if device["name"] not in bad_devices:
            devices.append(device["name"])
    return devices

def main():
    ...
    devices = get_blockdevices()
    for device in devices:
        drive = Drive(device)
        drive.load_data()
        line = f"drives,block_id={drive.drive_letter},node={drive.node},model={drive.model} tbw={drive.tbw} {drive.time}"
        print(influx_post_write_connector(line))

if __name__ == "__main__":
    main()
