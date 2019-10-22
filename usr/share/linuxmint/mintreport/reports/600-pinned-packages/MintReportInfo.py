import configparser
import os
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

from pkg_resources import parse_version
from mintreport import InfoReport, InfoReportAction

import urllib.request

class Package:

    def __init__(self, name):
        self.name = name
        self.version = None

class Release:

    def __init__(self, name):
        self.name = name
        self.packages = []

def find_pinned_packages(release):
    os.system("wget -O .tmp/sources.gz http://packages.linuxmint.com/dists/%s/upstream/source/Sources.gz 2> /dev/null" % release.name)
    os.system("gzip -d .tmp/sources.gz")
    os.system("mv .tmp/sources .tmp/%s" % release.name)
    with open(".tmp/%s" % release.name, 'r') as source_file:
        package = None
        for line in source_file:
            line = line.strip()
            if line.startswith("Package: "):
                name = line.replace("Package: ", "")
                package = Package(name)
                release.packages.append(package)
            elif line.startswith("Version: "):
                version = line.replace("Version: ", "")
                package.version = version

def find_ubuntu_updates(release):
    for component in ("main", "multiverse", "universe", "restricted"):
        os.system("wget -O .tmp/sources.gz http://archive.ubuntu.com/ubuntu/dists/%s-updates/%s/source/Sources.gz 2> /dev/null" % (release.name, component))
        os.system("gzip -d .tmp/sources.gz")
        os.system("mv .tmp/sources .tmp/%s" % component)
        with open(".tmp/%s" % component, 'r') as source_file:
            package = None
            for line in source_file:
                line = line.strip()
                if line.startswith("Package: "):
                    name = line.replace("Package: ", "")
                    package = Package(name)
                    release.packages.append(package)
                elif line.startswith("Version: "):
                    version = line.replace("Version: ", "")
                    package.version = version

class Report(InfoReport):

    def __init__(self):

        self.title = "Pinned updates are available"
        self.icon = "package-x-generic-symbolic"
        self.has_ignore_button = True
        self.descriptions = []
        self.actions = []
        self.dismissable_pkg_name = ""
        self.dismissable_pkg_version = ""
        self.dismissable_pkg_release = ""

    def is_pertinent(self):
        # Defines whether this report should show up

        self.settings = Gio.Settings("com.linuxmint.dev")
        dismissed_pins = self.settings.get_strv("dismissed-pins")

        os.system("mkdir -p .tmp")
        os.system("rm -rf .tmp/*")

        mint_couples = ['tricia=bionic', 'sylvia=xenial']
        is_pertinent = False
        for couple in mint_couples:
            (mint, ubuntu) = couple.split("=")
            mint = Release(mint)
            ubuntu = Release(ubuntu)
            find_pinned_packages(mint)
            find_ubuntu_updates(ubuntu)
            for mint_pkg in mint.packages:
                for ubuntu_pkg in ubuntu.packages:
                    if ubuntu_pkg.name == mint_pkg.name:
                        if ("%s=%s=%s" % (ubuntu_pkg.name, ubuntu_pkg.version, ubuntu.name)) not in dismissed_pins:
                            self.dismissable_pkg_name = ubuntu_pkg.name
                            self.dismissable_pkg_version = ubuntu_pkg.version
                            self.dismissable_pkg_release = ubuntu.name
                            self.descriptions.append("%s %s (in %s) is pinned by %s (in %s)" % (ubuntu_pkg.name, ubuntu_pkg.version, ubuntu.name, mint_pkg.version, mint.name))
                            self.actions.append(InfoReportAction(label="Dismiss %s %s (%s)" % (ubuntu_pkg.name, ubuntu_pkg.version, ubuntu.name), callback=self.dismiss))
                            is_pertinent = True

        return is_pertinent

    def get_descriptions(self):
        # Return the descriptions
        return self.descriptions

    def get_actions(self):
        # Return available actions
        return self.actions

    def dismiss(self):
        dismissed_pins = self.settings.get_strv("dismissed-pins")
        for pin in dismissed_pins:
            (pkg, version, release) = pin.split("=")
            if pkg == self.dismissable_pkg_name and release == self.dismissable_pkg_release:
                dismissed_pins.remove(pin)
        dismissed_pins.append("%s=%s=%s" % (self.dismissable_pkg_name, self.dismissable_pkg_version, self.dismissable_pkg_release))
        dismissed_pins.sort()
        self.settings.set_strv("dismissed-pins", dismissed_pins)
        # reload
        return True

if __name__ == "__main__":
    report = Report()
    print(report.is_pertinent())
