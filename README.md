# RTC Alarm for D-Link DNS320 L or rev. B2

Install dependencies (Debian):
```bash
$ apt-get install python python-serial python-pip
$ pip install click 
```

## How to use

```bash
Usage: ctl_alarm.py [OPTIONS] COMMAND [ARGS]...

Options:
  --debug / --no-debug
  --help                Show this message and exit.

Commands:
  disable
  read
  write
```

### read the alarm

```bash
$ ./ctl_alarm.py read 
Alarm is disabled
# or
$ ./ctl_alarm.py read 
Alarm is set to: 09.02. 20:22
```

### write the alarm

If not option for month, day or time is set the script will take the current date and
time values.

```bash
$ ./ctl_alarm.py write --help
Usage: ctl_alarm.py write [OPTIONS]

Options:
  -m, --month INTEGER  Month
  -d, --day INTEGER    Day
  -t, --time TEXT      Time HH:MM
  --help               Show this message and exit.

$ date
Mon Feb  9 20:26:39 CET 2015
$ ./ctl_alarm.py write -d 15 -t 11:42
Setting alarm to: 15.02. 11:42
```

### disable the alarm

```bash
$ ./ctl_alarm.py disable
Alarm is disabled
```

## About the D-Link DNS320 family

### D-Link DNS320 versioning


| Version        | CPU     | Memory | Notes                       |
| -------------- |:-------:|-------:|:---------------------------:|
| DNS320 rev. A  | 800Mhz  | 128Mb  | Fanspeed & Led's via sysfs  |
| DNS320 L       | 1000Mhz | 256Mb  | sysfs and microcontroller   |
| DNS320 rev. B2 | 1000Mhz | 128Mb  | same as DNS320L             |

Regarding the PCB and hardware housing the DNS320 revision is simply the L-version, just with less
RAM. This script is tested for the B2 version but should run as well on the DNS320 L.

## Credits / Links

### DNS-320 (Revision A)

* How to install Debian on the D-Link DNS-320 - http://jamie.lentin.co.uk/devices/dlink-dns325/
* Wiki with informations about the DNS-320 - http://dns323.kood.org/dns-320
* Hardware Mod and Info about the DNS-320 - http://www.baszerr.eu/doku.php/prjs/dns320/dns-320

### DNS-320 L

* Detailed information about the hardware and the microcontroller communication
  * http://www.aboehler.at/cms/projects-a-hacks/50-dns320l
  * Deamon for almost every controller function: http://www.aboehler.at/hg/dns320l-daemon (WOL 
is available but will not work with the D-Link hardware)
* U-boot information, Temperature sensor & fan deamon
  * https://github.com/martignlo/DNS-320L

### DNS-320 revision B

* Experimental alt-f support for the Revision B
  * https://groups.google.com/forum/#!topic/alt-f/vbDtHa8cjpU
  * http://sourceforge.net/projects/alt-f/files/Releases/0.1RC4.1/

## How this was build?

With information from the [dns320l-daemon](http://www.aboehler.at/hg/dns320l-daemon/file/1f945ce22321/dns320l-daemon.h), [fan-daemon.py](https://github.com/martignlo/DNS-320L/blob/master/fan-daemon.py) and some stock firmware tinkering with the [interceptty](http://www.suspectclass.com/sgifford/interceptty/interceptty.html) tool.
