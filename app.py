#!/bin/python3

# -*- coding: utf-8 -*-

from typing import Optional
from flask import Flask, render_template, send_file, request
import os
import requests
from gevent.pywsgi import WSGIServer
import json

app = Flask(__name__)


def load_vars(config_filename: str = "config.json"):
    try:
        data = None
        with open(config_filename) as json_file:
            data = json.load(json_file)

        VARS.endpoint = data["endpoint"]
        VARS.secret_key = data["secret_key"]
        VARS.server_port = data["server_port"]

        return True
    
    except: return False

class VARS: #default vars, you still need a json.
    endpoint = "https://mcdl.nixuge.me/get_data/"
    secret_key = "4k9Mu1AoQHGh0x"
    server_port = 64670


class Link:
    def __init__(self, url: str, key: Optional[str]):
        self.full_url = url
        
        #flask issue for the lines below
        if not "https:/" in self.full_url and not "http:/" in self.full_url:
            self.full_url = "https:/" + self.full_url

        self._fix_full_url("https:/", "https://")
        self._fix_full_url("http:/", "http://")

        self.cropped_url = self.full_url.replace("https://", "").replace("http://", "")
        
        self.hostname = self.cropped_url.split('/')[0]
        self.domain = '.'.join(self.hostname.split('.')[-2:])
        
        self.data_path = "data/" + self.cropped_url
        self.data_folder = os.path.dirname(self.data_path)
        self.extension = self.cropped_url.split('.')[-1]

        self.is_trusted = self._check_trust(key)

    def _fix_full_url(self, original: str, new: str):
        #made for https:/->https://
        if original in self.full_url and not new in self.full_url: 
            self.full_url = self.full_url.replace(original, new)

    def _check_trust(self, key: Optional[str]) -> bool:
        trusted_domains = [
            "minecraft.net",
            "mojang.com",
            "multimc.org",
            "polymc.org",
            "prismlauncher.org",
            "maven.org",
            "fabricmc.net",
            "quiltmc.org",
            "minecraftforge.net",
            "apache.org",
            "liteloader.com"
        ]
        trusted_hostnames = [
            "polymc.github.io",
            "prismlauncher.github.io",
            "multimc.github.io"
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

        file_content = file_content.replace("https://", VARS.endpoint)
        return file_content
    
    @staticmethod
    def _patch_forge_file_polymc(file_content: str):
        file_dict = json.loads(file_content)
        
        #if no libs key (eg in the index), just return the original)
        if not file_dict.get("libraries"): 
            return file_content
        
        #some libraries have no "url" value in their dict, just their name
        #when this happens, mc should download from libraries.minecraft.net, and will
        #however, we want it to download from our website instead
        #hence why we're explicitely adding the key so it gets replaced
        for entry in file_dict.get("libraries"):
            if not entry.get("url"):
                entry["url"] = "https://libraries.minecraft.net"

        return json.dumps(file_dict)


@app.route("/meta/<path:path>")
def get_meta(path: str = ""):
    full_path = "meta/" + path
    if not os.path.exists(full_path): return "404", 404

    return send_file(full_path), 200


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
    return render_template("index.html")


if __name__ == "__main__":
    if not load_vars():
        print("Issue loading the config ! make sure it's there and that everything is set correctly")
        exit(1)

    http_server = WSGIServer(('', VARS.server_port), app)
    http_server.serve_forever()