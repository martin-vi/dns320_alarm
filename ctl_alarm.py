#!/usr/bin/env python2

import sys
import click
from dateutil import tz
from lib320Alarm import SerialConnection, NasAlarm, NasDateTime
from datetime import datetime, timedelta

now = datetime.now()

def format_alarm(dtime):
    return dtime.strftime(NasAlarm.alarm_format)

def format_dtime(dtime):
    return dtime.strftime(NasAlarm.rtc_format)

def echo_alarm(alarm_time, disable=False):
    if not alarm_time:
        click.echo('Alarm is disabled')
        return

    if disable:
        msg_text = 'disabling Alarm failed, '
    else:
        msg_text = ''
    alarm_time_str = format_alarm(alarm_time)
    click.echo('{}Alarm is set to: {}'.format(msg_text, alarm_time_str))

@click.group()
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, debug):
    ctx.obj['DEBUG'] = debug
    ctx.obj['SERIAL'] = SerialConnection(debug=ctx.obj['DEBUG'])

@cli.command()
@click.option('-m', '--month', default=now.month, help='Month')
@click.option('-d', '--day', default=now.day, help='Day')
@click.option('-t', '--time', default=now.strftime('%H:%M'), help='Time HH:MM')
@click.option('--next-weekday', default=None, type=int, help='Next weekday (0 is Monday and Sunday is 6.)')
@click.pass_context
def write(ctx, month, day, time, next_weekday):
    try:
        time_parsed = datetime.strptime(time, '%H:%M')
        hour = time_parsed.hour
        minute = time_parsed.minute
    except ValueError:
        click.echo('time option is in wrong {} format shoud be HH:MM'.format(time))
        return

    if next_weekday is not None:
        if not (0 <= next_weekday < 7):
            click.echo('invalid weekday setting {}'.format(next_weekday))
        elif now.weekday() == next_weekday:
            diff_weekdays = 7
        else:
            diff_weekdays = ((6-now.weekday()) + next_weekday) % 6
            if now.weekday() > next_weekday:
                diff_weekdays += 1
    else:
        diff_weekdays = 0
        if month < 1 or month > 12:
            click.echo('invalid month option {}'.format(month))
            return
        elif day < 1 or day > 31:
            click.echo('invalid day option {}'.format(month))
            return

    wakeup_time = datetime(now.year, month, day, hour, minute) + timedelta(days=diff_weekdays)
    click.echo('Setting alarm to: {}'.format(format_alarm(wakeup_time)))

    alarm = NasAlarm(ctx.obj['SERIAL'])
    alarm.setAlarm(wakeup_time)

@cli.command()
@click.option('-w', '--systohc', is_flag=True, help='Set the Hardware Clock from the System Clock.')
@click.option('-s', '--hctosys', is_flag=True, help='Set the System Clock from the Hardware Clock.')
@click.pass_context
def rtc(ctx, systohc, hctosys):
    nas_dt = NasDateTime(ctx.obj['SERIAL'])

    assert not(systohc and hctosys), 'Invalid argument combination'
    if systohc:
        click.echo('writing system clock to hardware clock')
        nas_dt.setDateTime()

    dt = nas_dt.getDateTime(set_sys=hctosys)
    click.echo('RTC date and time is set to: {}'.format(format_dtime(dt)))

@cli.command()
@click.pass_context
def disable(ctx):
    alarm = NasAlarm(ctx.obj['SERIAL'])
    alarm.disableAlarm()
    echo_alarm(alarm.getAlarm(), disable=True)

@cli.command()
@click.pass_context
def read(ctx):
    alarm = NasAlarm(ctx.obj['SERIAL'])
    echo_alarm(alarm.getAlarm())

def uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return timedelta(seconds = uptime_seconds)

@cli.command()
@click.option('-o', '--offset', default=5, type=int, help='Test if boot is scheduled, offset in minutes.')
@click.option('--use-now', is_flag=True)
@click.pass_context
def is_scheduled(ctx, offset, use_now):
    exit_code = 1

    alarm = NasAlarm(ctx.obj['SERIAL'])
    alarm_time = alarm.getAlarm()
    if not alarm_time:
        click.echo('Scheduled boot time is disabled.')
        sys.exit(exit_code)

    boot_time = datetime.now(tz=tz.tzlocal())
    if not use_now:
        boot_time -= uptime()
    offset = timedelta(minutes=offset)

    click.echo('Boot time is: {}'.format(format_alarm(boot_time)))
    if (alarm_time - offset) <= boot_time <= (alarm_time + offset):
        click.echo('Boot triggered by alarm.')
        exit_code = 0
    elif boot_time > alarm_time:
        click.echo('Boot was triggered after the alarm (offset {0} minutes).'.format(offset))
    else:
        click.echo('Boot is before schedule (offset {0} minutes).'.format(offset))
    echo_alarm(alarm_time)
    sys.exit(exit_code)


if __name__ == '__main__':
    cli(obj={})

