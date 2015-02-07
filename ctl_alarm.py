#!/usr/bin/env python2

import click
from lib320Alarm import SerialConnection, NasAlarm
from datetime import datetime

now=datetime.now()

def format_dtime(dtime):
    return dtime.strftime(NasAlarm.date_format)

def echo_alarm(alarm_time, disable=False):
    if not alarm_time:
        click.echo('Alarm is disabled')
        return

    if disable:
        msg_text = 'disabling Alarm failed, '
    else:
        msg_text = ''
    alarm_time_str = format_dtime(alarm_time)
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
@click.pass_context
def write(ctx, month, day, time):
    if month < 1 or month > 12:
        click.echo('invalid month option {}'.format(month))
        return
    elif day < 1 or day > 31:
        click.echo('invalid day option {}'.format(month))
        return

    try:
        time_parsed = datetime.strptime(time, '%H:%M')
        hour = time_parsed.hour
        minute = time_parsed.minute
    except ValueError:
        click.echo('time option is in wrong {} format shoud be HH:MM'.format(time))
        return

    wakeup_time = datetime(now.year, month, day, hour, minute)
    click.echo('Setting alarm to: {}'.format(format_dtime(wakeup_time)))

    alarm = NasAlarm(ctx.obj['SERIAL'])
    alarm.setAlarm(wakeup_time)

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

if __name__ == '__main__':
    cli(obj={})
