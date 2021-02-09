const Applet = imports.ui.applet;
const Lang = imports.lang;
const Mainloop = imports.mainloop;
const PopupMenu = imports.ui.popupMenu;
const Main = imports.ui.main;
const GLib = imports.gi.GLib;
const Cinnamon = imports.gi.Cinnamon;
const GTop = imports.gi.GTop;
const Settings = imports.ui.settings;
const Clutter = imports.gi.Clutter;

const REFRESH_RATE = 1000;
const FLAT_RANGE = 5; // (+/- xx kb/min)


const MB = 1048576;
const KB =    1024;
const MINUTE = 60000;

function MyApplet(orientation, panel_height, instance_id) {
    this._init(orientation, panel_height, instance_id);
}


MyApplet.prototype = {
    __proto__: Applet.TextIconApplet.prototype,

    _init: function(orientation, panel_height, instance_id) {        
        Applet.TextIconApplet.prototype._init.call(this, orientation, panel_height, instance_id);

        this._applet_label.set_style("font-weight: normal;");

        this.process_display_name = "Cinnamon";

        this.settings = new Settings.AppletSettings(this, "cinnamonitor@cinnamon.org", instance_id);

        this.settings.bindProperty(Settings.BindingDirection.IN,
                                 "process-name",
                                 "process_name",
                                 this.on_settings_changed,
                                 null);

        this.on_settings_changed();

        this.pulse_timer_id = 0;

        this._orientation = orientation;
        this.initialTime = new Date();
    },

    get_pid_for_process_name: function (name) {
        let success, stdout, stderr, code, error;
        [success, stdout, stderr, code, error] = GLib.spawn_command_line_sync("ps -eo \"\%p,\%c\"");

        let pid = global.get_pid();
        this.process_display_name = "Cinnamon";

        let lines = stdout.toString().split("\n");

        for (let line in lines) {
            try {
                if (lines[line].indexOf("<defunct>") > -1) {
                    continue;
                }

                let split_line = lines[line].replace(" ", "").split(",");
                if (split_line.length == 2 && split_line[1] == name) {
                    pid = split_line[0];
                    this.process_display_name = name;
                    break;
                }
            } catch (e) {
                continue;
            }
        }
        return pid;
    },

    on_settings_changed: function () {
        if (this.process_name == "")
            this.pid = global.get_pid();
        else
            this.pid = this.get_pid_for_process_name(this.process_name);
        this.cinnamonMem = new CinnamonMemMonitor(this.pid);

        this._applet_label.set_x_align(Clutter.ActorAlign.CENTER);
        this._applet_label.set_x_expand(true);

        let test_string;

        if (this.pid.toString() == global.get_pid().toString()) {
            test_string = "cinnamon: 00000.00m, 100.0%";
        } else {
            test_string = this.process_name + ": 00000.00m, 100.0%";
        }

        let layout = this._applet_label.create_pango_layout(test_string);
        let w, h;
        [w, h] = layout.get_pixel_size();
        this.actor.natural_width = w;
    },

    _pulse: function() {
        this.cinnamonMem.update();
        let now = new Date();
        let elapsed = (now.getTime() - this.initialTime.getTime()) / MINUTE; // get elapsed minutes
        let delta = this.cinnamonMem.getDiffKb() / elapsed;
        let ttip;
        if (delta > FLAT_RANGE) {
            ttip = "+" + delta.toFixed(2) + "k/min\n";
        } else if (delta < -FLAT_RANGE) {
            ttip = delta.toFixed(2) + "k/min\n";
        } else {
            ttip = "flat\n";
        }
        ttip += "-------\n";
        ttip += "Process: " + this.process_display_name + "\n";
        ttip += "PID: " + this.pid.toString() + "\n";
        let time = secondsToTime(elapsed * 60);
        ttip += "Elapsed: " + time.h + ":" + time.m + ":" + time.s + "\n";
        ttip += "-------\n";
        ttip += "Start: " + this.cinnamonMem.getStartMb().toFixed(2) + "m\n";
        ttip += "Diff: " + this.cinnamonMem.getDiffMb().toFixed(2) + "m\n";
        ttip += "Max: " + this.cinnamonMem.getMaxMb().toFixed(2) + "m\n";
        ttip += "-------\n";
        ttip += "Acc. CPU%: " + (this.cinnamonMem.getCinnamonAccumulatedCpuUsage()*100).toPrecision(3) + "\n";
        ttip += "Acc. Total CPU%: " + (this.cinnamonMem.getTotalAccumulatedCpuUsage()*100).toPrecision(3) + "\n";
        ttip += "-------\n";
        ttip += "click to reset or reconnect to the process";

        let curMb = this.cinnamonMem.getCurMb().toFixed(2);
        let cpuUsage = (this.cinnamonMem.getCpuUsage()*100).toFixed(1);
        
        let label;

        if (this.process_display_name == "Cinnamon") {
            label = curMb + "m, " + cpuUsage + "%";
        } else {
            label = this.process_display_name + ": " + curMb + "m, " + cpuUsage + "%";
        }

        this.set_applet_label(label);

        this.set_applet_tooltip(ttip);
        return true;
    },

    stop_pulse: function() {
        if (this.pulse_timer_id > 0) {
            Mainloop.source_remove(this.pulse_timer_id);
            this.pulse_timer_id = 0;
        }
    },

    on_applet_added_to_panel: function() {
        this.stop_pulse();

        this.pulse_timer_id = Mainloop.timeout_add(REFRESH_RATE, Lang.bind(this, this._pulse));
    },

    on_applet_removed_from_panel: function(event) {
        this.stop_pulse();
    },

    on_applet_clicked: function(event) {
        this.initialTime = new Date();
        this.on_settings_changed();
    },
    
    on_orientation_changed: function (orientation) {
        this._orientation = orientation;
        // this._initContextMenu();
    }
};

function CinnamonMemMonitor(pid) {
    this._init(pid);
}

CinnamonMemMonitor.prototype = {

    _init: function(pid) {
        try {
            this.pid = pid;
            this.procMem = new GTop.glibtop_proc_mem();
            this.procTime = new GTop.glibtop_proc_time();
            this.gtop = new GTop.glibtop_cpu();
            this.maxMem = 0;

            this.resetStats();
        } catch (e) {
            global.logError(e);
        }
    },

    update: function() {
        GTop.glibtop_get_proc_mem(this.procMem, this.pid);
        this.lastRtime = this.procTime.rtime;
        this.lastTick = this.gtop.total;
        GTop.glibtop_get_proc_time(this.procTime, this.pid);
        GTop.glibtop_get_cpu(this.gtop);

        if (this.maxMem < this.procMem.resident) {
            this.maxMem = this.procMem.resident;
        }
    },
    
    getCpuUsage: function() {
        let delta = this.procTime.rtime - this.lastRtime;
        let tickDelta = this.gtop.total - this.lastTick;
        return tickDelta ? delta/tickDelta : 0;
    },

    getCinnamonAccumulatedCpuUsage: function() {
        let delta = this.procTime.rtime - this.startRtime;
        let tickDelta = this.gtop.total - this.startTicks;
        return tickDelta ? delta/tickDelta : 0;
    },

    getTotalAccumulatedCpuUsage: function() {
        let delta = this.gtop.idle - this.startIdle;
        let tickDelta = this.gtop.total - this.startTicks;
        return 1 - (tickDelta ? delta/tickDelta : 0);
    },

    getCurMb: function() {
        return this.procMem.resident/MB;
    },

    getStartMb: function() {
        return this.startMem/MB;
    },

    getMaxMb: function() {
        return this.maxMem / MB;
    },

    getDiffMb: function() {
        return (this.procMem.resident - this.startMem)/MB;
    },

    getDiffKb: function() {
        return (this.procMem.resident - this.startMem)/KB;
    },

    resetStats: function() {
        this.update();
        this.startMem = this.procMem.resident;
        this.startRtime = this.procTime.rtime;
        this.startTicks = this.gtop.total;
        this.startIdle = this.gtop.idle;
        this.maxMem = this.startMem;
    }
};

function main(metadata, orientation, panel_height, instance_id) {  
    let myApplet = new MyApplet(orientation, panel_height, instance_id);
    return myApplet;      
}


function secondsToTime(secs)
{
    let hours = Math.floor(secs / (60 * 60));
    let divisor_for_minutes = secs % (60 * 60);
    let minutes = Math.floor(divisor_for_minutes / 60);

    let divisor_for_seconds = divisor_for_minutes % 60;
    let seconds = Math.floor(divisor_for_seconds);
    let obj = {
            "h": hours,
            "m": minutes < 10 ? "0" + minutes: minutes,
            "s": seconds < 10 ? "0" + seconds: seconds
    };
    return obj;
}
