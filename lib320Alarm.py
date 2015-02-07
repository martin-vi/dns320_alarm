#!/usr/bin/env python2

import serial
import time
from datetime import datetime, timedelta
from dateutil import tz

RAlarmMonthCmd =        "\xfa\x01\x0a\x01\x01\x00\xfb"
RAlarmDateCmd =         "\xfa\x01\x0b\x01\x01\x00\xfb"
RAlarmHourCmd =         "\xfa\x01\x0c\x01\x01\x00\xfb"
RAlarmMinuteCmd =       "\xfa\x01\x0d\x01\x01\x00\xfb"
#RAlarmSecondCmd =       "\xfa\x01\x0e\x01\x01\x00\xfb"

WAlarmMonthCmd =        "\xfa\x01\x0a\x02\x01\x00\xfb"
WAlarmDateCmd =         "\xfa\x01\x0b\x02\x01\x00\xfb"
WAlarmHourCmd =         "\xfa\x01\x0c\x02\x01\x00\xfb"
WAlarmMinuteCmd =       "\xfa\x01\x0d\x02\x01\x00\xfb"
#WAlarmSecondCmd =       "\xfa\x01\x0e\x02\x01\x00\xfb"

WAlarmEnableCmd =       "\xfa\x01\x10\x02\x01\x01\xfb"
WAlarmDisableCmd =      "\xfa\x01\x10\x02\x01\x00\xfb"

DATA_BIT = 5
DATE_FORMAT = '%d.%m. %H:%M'

def to_hex_base8(integer):
    # e.g. 50 to \x50 equals printable ascii char 'P'

    #cmdBuf[i] = ((cmdBuf[i] / 10) << 4) + (cmdBuf[i] % 10);
    return chr( integer + ( integer / 10 ) * 6 )

def to_int(hex_val):
    try:
        temp = ord(hex_val)
        #buf[i] = (buf[i] & 0x0f) + 10 * ((buf[i] & 0xf0) >> 4);
        return ( temp >> 4 ) * 10 + ( temp & 0x0f )
    except TypeError:
        return None

def localTZ(dtime):
    if dtime.tzinfo:
        return dtime.astimezone(tz.tzlocal())
    else:
        return dtime.replace(tzinfo=tz.tzlocal())

class serial_connection(object):

    device = "/dev/ttyS1"
    baudrate = 115200

    def __init__(self):
        self.port = serial.Serial(self.device, self.baudrate, 8, "N", 1, 0.1)

    def write(self, data):
        assert len(data) == 7
        #print 'set value: ' + repr(data)
        self.port.write(data)
        self.port.flush()

    def write_value(self, command, value):
        try:
            data = to_hex_base8(value)
        except (ValueError, TypeError):
            return False

        cmd = command[:DATA_BIT] \
                + data \
                + command[DATA_BIT+1:]
        self.write(cmd)
        return True

    def _read(self, timeout=5):
       tstamp = time.time()
       while time.time() - tstamp < timeout:
          data = self.port.read(7)
          if data and len(data) == 7 and data[0] == "\xfa":
             return data
          return None

    def getData(self):
        data, _ = self._read(), self._read()
        #print 'read data: ' + repr(data)
	return data

    def set_and_get(self, data):
        self.write(data)
        value = self.getData()
        try:
            return to_int(value[DATA_BIT])
        except:
            return None

    def scrub(self):
        while self.getData():
            pass


class nas_alarm(object):

    def __init__(self, serial_connection):
        self._ser = serial_connection

    def __str__(self):
        wakeup = self.getAlarm()
        if not wakeup:
            return 'no alarm time set'
        else:
            return wakeup.strftime(DATE_FORMAT)

    def getAlarm(self):
        self._ser.scrub()
        hour, minute = self.__getTime()
        month, date = self.__getDate()

        try:
            dtime = datetime( datetime.now().year,
                month, date, hour, minute, tzinfo=tz.tzutc())
            return localTZ(dtime)
        except (TypeError, ValueError):
            return None

    def __getDate(self):
        date = self._ser.set_and_get(RAlarmDateCmd)
        month = self._ser.set_and_get(RAlarmMonthCmd)
        return (month, date)

    def __getTime(self):
        minute = self._ser.set_and_get(RAlarmMinuteCmd)
        hour = self._ser.set_and_get(RAlarmHourCmd)
        return (hour, minute)

    def setAlarm(self, dtime, check=True):
        dtime = localTZ(dtime).astimezone(tz.tzutc())

        self._ser.scrub()

        success = self.__setTime(dtime.hour, dtime.minute)
        success &= self.__setDate(dtime.month, dtime.day)
        self.__enableAlarm()

        if check: self.__checkAlarm(dtime)
        return success

    def __setDate(self, month, day):
        success = self._ser.write_value(WAlarmDateCmd, day)
        success &= self._ser.write_value(WAlarmMonthCmd, month)
        return success
        
    def __setTime(self, hour, minute):
        success = self._ser.write_value(WAlarmMinuteCmd, minute)
        success &= self._ser.write_value(WAlarmHourCmd, hour)
        return success

    def __enableAlarm(self):
        return self._ser.write(WAlarmEnableCmd)

    def __disableAlarm(self):
        return self._ser.write(WAlarmDisableCmd)

    def __checkAlarm(self, dtime):
        readTime = str(self)
        setTime = localTZ(dtime).strftime(DATE_FORMAT)

        while readTime != setTime:
            print 'read alarm time (%s) doesn\'t match the new alarm (%s) time, retry' % (readTime, setTime)
            time.sleep(3)
            self.setAlarm(dtime, check=False)
            readTime = str(self)

if __name__ == '__main__':
    """
    To test the lib exec lib320Alarm.py and poweroff
    the device. It should power up in about 3 minutes.
    """
    
    print 'current time: ' + datetime.now().strftime(DATE_FORMAT)

    serial_connection = serial_connection()
    alarm = nas_alarm(serial_connection)

    print 'old wakeup time: ' + str(alarm)

    wakeup = datetime.now() + timedelta(minutes=3)
    alarm.setAlarm(wakeup)

    print 'new wakup time: ' + wakeup.strftime(DATE_FORMAT)
