import configparser
import os
import subprocess
import gi
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

from pkg_resources import parse_version
from mintreport import InfoReport, InfoReportAction

import urllib.request

def find_mint_version(release_name, package_name):
    # return "1.0"

    os.system("rm -f .info-report/*")
    os.system("wget -O .info-report/%s.gz http://packages.linuxmint.com/dists/%s/upstream/source/Sources.gz 2> /dev/null" % (release_name, release_name))
    os.system("gzip -d .info-report/%s.gz" % release_name)
    with open(".info-report/%s" % release_name, 'r') as source_file:
        package = None
        for line in source_file:
            line = line.strip()
            if line.startswith("Package: "):
                name = line.replace("Package: ", "")
            elif line.startswith("Version: "):
                version = line.replace("Version: ", "")
                if name == package_name:
                    return version
        source_file.close()
    return None

class Report(InfoReport):

    def __init__(self):

        self.title = "A new version of Chromium is available"
        self.icon = "network-workgroup-symbolic"
        self.has_ignore_button = True
        self.descriptions = []
        self.actions = []

    def is_pertinent(self):
        # Defines whether this report should show up

        self.settings = Gio.Settings("com.linuxmint.dev")

        os.system("mkdir -p .info-report")
        os.system("rm -rf .info-report/*")

        # Find the Mint version
        mint_version_str = find_mint_version("ulyana", "chromium")
        mint_version = mint_version_str.split("~")[0]
        # mint_version = mint_version_str

        current_version = parse_version(mint_version)
        # Find the latest versions of Chromium

        chromium_json = None
        broken = False

        self.beta_version_str = 0
        self.release_version_str = 0

        with urllib.request.urlopen("https://omahaproxy.appspot.com/all.json") as f:
            try:
                chromium_json = json.loads(f.read())
            except Exception as e:
                print(e)
                broken = True

        for platform in chromium_json:
            if platform["os"] == "linux":
                for version in platform["versions"]:
                    if version["channel"] == "stable":
                        self.release_version_str = version["version"]
                    if version["channel"] == "beta":
                        self.beta_version_str = version["version"]

        os.system("rm -rf .info-report")

        dismissed_releases = self.settings.get_strv("dismissed-releases")

        found_releases = False
        if parse_version(self.beta_version_str) > parse_version(mint_version) and ("chromium-beta=%s" % self.beta_version_str) not in dismissed_releases:
            self.descriptions.append("Version %s BETA is available upstream (Mint has %s)." % (self.beta_version_str, mint_version_str))
            self.actions.append(InfoReportAction(label="Dismiss Chromium %s BETA" % self.beta_version_str, callback=self.dismiss_chromium_beta))
            found_releases = True
        if parse_version(self.release_version_str) > parse_version(mint_version) and ("chromium-release=%s" % self.release_version_str) not in dismissed_releases:
            self.descriptions.append("Version %s RELEASE is available upstream (Mint has %s)." % (self.release_version_str, mint_version_str))
            self.actions.append(InfoReportAction(label="Dismiss Chromium %s RELEASE" % self.release_version_str, callback=self.dismiss_chromium_release))
            found_releases = True

        return found_releases

    def get_descriptions(self):
        # Return the descriptions
        return self.descriptions

    def get_actions(self):
        # Return available actions
        return self.actions

    def dismiss_chromium_beta(self, data):
        dismissed_releases = self.settings.get_strv("dismissed-releases")
        for release in dismissed_releases:
            if release.startswith("chromium-beta="):
                dismissed_releases.remove(release)
        dismissed_releases.append("chromium-beta=%s" % self.beta_version_str)
        dismissed_releases.sort()
        self.settings.set_strv("dismissed-releases", dismissed_releases)
        # don't reload
        return True

    def dismiss_chromium_release(self, data):
        dismissed_releases = self.settings.get_strv("dismissed-releases")
        for release in dismissed_releases:
            if release.startswith("chromium-release="):
                dismissed_releases.remove(release)
        dismissed_releases.append("chromium-release=%s" % self.release_version_str)
        dismissed_releases.sort()
        self.settings.set_strv("dismissed-releases", dismissed_releases)
        # don't reload
        return True

if __name__ == "__main__":
    report = Report()
    print(report.is_pertinent())
