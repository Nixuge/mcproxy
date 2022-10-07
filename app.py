#!/bin/python3

# -*- coding: utf-8 -*-

from typing import Optional
from flask import Flask, send_file, request
import os
import requests
from gevent.pywsgi import WSGIServer
import json


app = Flask(__name__)

class VARS:
    endpoint_b = "https://mcdl.nixuge.me/get_data/"
    secret_key = "4k9Mu1AoQHGh0x"
    server_port = 64670


class Link:
    def __init__(self, url: str, key: Optional[str]):
        self.full_url = url
        
        #flask issue for the lines below
        if not "https:/" in self.full_url and not "http:/" in self.full_url:
            self.full_url = "https:/" + self.full_url

        if "https:/" in self.full_url and not "https://" in self.full_url: 
            self.full_url = self.full_url.replace("https:/", "https://")
        if "http:/" in self.full_url and not "http://" in self.full_url:
            self.full_url = self.full_url.replace("http:/", "http://")

        self.cropped_url = self.full_url.replace("https://", "").replace("http://", "")
        
        self.hostname = self.cropped_url.split('/')[0]
        self.domain = '.'.join(self.hostname.split('.')[-2:])
        
        self.data_path = "data/" + self.cropped_url
        self.data_folder = os.path.dirname(self.data_path)
        self.extension = self.cropped_url.split('.')[-1]

        self.is_trusted = self._check_trust(key)

    def _check_trust(self, key: str) -> bool:
        trusted_domains = [
            "minecraft.net",
            "mojang.com",
            "multimc.org",
            "polymc.org",
            "maven.org",
            "fabricmc.net",
            "quiltmc.org",
            "minecraftforge.net",
            "apache.org",
            "liteloader.com"
        ]
        trusted_hostnames = [
            "polymc.github.io"
        ]
        
        return self.domain in trusted_domains \
            or self.hostname in trusted_hostnames \
            or key == VARS.secret_key

    def data_exists(self) -> bool:
        return os.path.exists(self.data_path)

    def _create_folders(self) -> None:
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

    def download_file(self) -> None:
        self._create_folders()
        r = requests.get(self.full_url)

        if self.extension == "json": 
            with open(self.data_path, "w") as open_file:
                open_file.write(Utils.patch_file(r.text, self.cropped_url))
        
        else: 
            with open(self.data_path, "wb") as open_file:
                open_file.write(r.content)



    
class Utils:
    @staticmethod
    def patch_file(file_content: str, url: str):
        
        if "/net.minecraftforge/" in url:
            file_content = Utils._patch_forge_file_polymc(file_content)

        file_content = file_content.replace("https://", VARS.endpoint_b)
        return file_content
    
    @staticmethod
    def _patch_forge_file_polymc(file_content: str):
        file_dict = json.loads(file_content)
        
        #if no libs key (eg in the index), just return the original)
        if not file_dict.get("libraries"): 
            return file_content
        
        #some libraries have no "url" value in their dict, just their name
        #that means the libs will be downloaded from the default url (libs.minecraft.net)
        #we don't want that, so we're adding the url key here so it's replaced.
        for entry in file_dict.get("libraries"):
            if not entry.get("url"):
                entry["url"] = "https://libraries.minecraft.net"

        return json.dumps(file_dict)


@app.route("/get_data/<path:path>")
def get_data(path: str = ""):
    link = Link(path, request.args.get('key'))

    if not link.is_trusted:
        return "Must be from a trusted domain !", 400

    if not link.data_exists():
        link.download_file()

    return send_file(link.data_path), 200


@app.route("/")
def index():
    return "Welcome to le super index fifou trop bien. Pr linstant lexe est po la pck g la flemme voila nsm il est sur ma cle usb ca suffit tres bien mtn demerdez vous mais en gros si qqun veut fo recompiler PolyMC et ds le CMakeList.txt changer 'meta.polymc.org' à 'mcdl.nixuge.me/get_data/meta.polymc.org' et apres cbon voila bon chonc"


if __name__ == "__main__":
    http_server = WSGIServer(('', VARS.server_port), app)
    http_server.serve_forever()

