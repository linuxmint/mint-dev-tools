import configparser
import os
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

from pkg_resources import parse_version
from mintreport import InfoReport, InfoReportAction

import urllib.request

def find_mint_version(release_name, package_name):
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

        self.title = "A new version of Firefox is available"
        self.icon = "network-workgroup-symbolic"
        self.has_ignore_button = True
        self.descriptions = []
        self.actions = []

    def is_pertinent(self):
        # Defines whether this report should show up

        self.settings = Gio.Settings("com.linuxmint.dev")

        os.system("mkdir -p .info-report")
        os.system("rm -rf .info-report/*")

        # Find the Mint versions
        mint_version_str = find_mint_version("tricia", "firefox")
        mint_version = mint_version_str.split("+")[0]
        mint_esr_str = find_mint_version("cindy", "firefox")
        mint_esr = mint_esr_str.split("~")[0]

        # Find the latest versions of Firefox and Firefox ESR
        content = urllib.request.urlopen("https://download-installer.cdn.mozilla.net/pub/firefox/releases/").read().decode("utf8")
        split_string = "<tr"
        ignore_lines_start = 4
        self.max_version = "0"
        self.max_esr = "0esr"
        for release in content.split(split_string)[ignore_lines_start:]:
            version = release.split("<a href=\"")[1].split("/\"")[0]
            version = version.split("/")[-1]
            if version[0] in "0123456789" and not "b" in version and not "RC" in version and not "BETA" in version and not "funnelcake" in version:
                if "esr" in version:
                    if parse_version(version) > parse_version(self.max_esr):
                        self.max_esr = version
                else:
                    if parse_version(version) > parse_version(self.max_version):
                        self.max_version = version

        os.system("rm -rf .info-report")

        dismissed_releases = self.settings.get_strv("dismissed-releases")

        found_releases = False
        if parse_version(self.max_version) > parse_version(mint_version) and ("firefox=%s" % self.max_version) not in dismissed_releases:
            self.descriptions.append("Version %s is available upstream (Mint has %s)." % (self.max_version, mint_version_str))
            self.actions.append(InfoReportAction(label="Dismiss Firefox %s" % self.max_version, callback=self.dismiss_firefox))
            found_releases = True
        if parse_version(self.max_esr) > parse_version(mint_esr.split("~")[0]) and ("firefox-esr=%s" % self.max_esr) not in dismissed_releases:
            self.descriptions.append("Version %s is available upstream (Mint has %s)." % (self.max_esr, mint_esr_str))
            self.actions.append(InfoReportAction(label="Dismiss Firefox %s" % self.max_esr, callback=self.dismiss_esr))
            found_releases = True

        return found_releases

    def get_descriptions(self):
        # Return the descriptions
        return self.descriptions

    def get_actions(self):
        # Return available actions
        return self.actions

    def dismiss_esr(self):
        dismissed_releases = self.settings.get_strv("dismissed-releases")
        for release in dismissed_releases:
            if release.startswith("firefox-esr="):
                dismissed_releases.remove(release)
        dismissed_releases.append("firefox-esr=%s" % self.max_esr)
        dismissed_releases.sort()
        self.settings.set_strv("dismissed-releases", dismissed_releases)
        # don't reload
        return True

    def dismiss_firefox(self):
        dismissed_releases = self.settings.get_strv("dismissed-releases")
        for release in dismissed_releases:
            if release.startswith("firefox="):
                dismissed_releases.remove(release)
        dismissed_releases.append("firefox=%s" % self.max_version)
        dismissed_releases.sort()
        self.settings.set_strv("dismissed-releases", dismissed_releases)
        # don't reload
        return True

if __name__ == "__main__":
    report = Report()
    print(report.is_pertinent())
