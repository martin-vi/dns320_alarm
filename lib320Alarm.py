#!/usr/bin/env python2

import os
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

RDateAndTimeCmd =       "\xfa\x01\x08\x01\x01\x00\xfb"
#                                             sec min  h wday mday mon year
WDateAndTimeCmd =       "\xfa\x01\x08\x02\x07\x17\x06\x21\x02\x10\x09\x13\xfb"

DATA_BIT = 5

class SerialReadError(Exception):
    pass

class AlarmDisabledException(Exception):
    pass

def to_hex_base8(integer):
    # e.g. 50 to \x50 equals printable ascii char 'P'
    #cmdBuf[i] = ((cmdBuf[i] / 10) << 4) + (cmdBuf[i] % 10);
    return chr( integer + ( integer / 10 ) * 6 )

def to_int(hex_val):
    temp = ord(hex_val)
    #buf[i] = (buf[i] & 0x0f) + 10 * ((buf[i] & 0xf0) >> 4);
    return ( temp >> 4 ) * 10 + ( temp & 0x0f )

def localTZ(dtime):
    if dtime.tzinfo:
        return dtime.astimezone(tz.tzlocal())
    else:
        return dtime.replace(tzinfo=tz.tzlocal())

class SerialConnection(object):

    device = "/dev/ttyS1"
    baudrate = 115200

    def __init__(self, debug=False):
        self.port = serial.Serial(self.device, self.baudrate, 8, "N", 1, 0.1)
        self._debug=debug

    def write(self, data, size=7):
        assert len(data) == size
        if self._debug: print 'set value: ' + repr(data)
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

    def _read(self, timeout=5, size=7):
       tstamp = time.time()
       while time.time() - tstamp < timeout:
          data = self.port.read(size)
          if data and len(data) == size and data[0] == "\xfa":
             return data
          return None

    def getData(self):
        data, _ = self._read(), self._read()
        if self._debug: print 'read data: ' + repr(data)
	return data

    def set_and_get(self, data, retry=3):
        for i in range(retry):
            self.scrub()
            self.write(data)
            read_data = self.getData()

            if not read_data:
                if self._debug: print 'read data failed - retry'
                continue
            elif data[:DATA_BIT] != read_data[:DATA_BIT]:
                if self._debug: print 'invalid data - retry'
                continue
            try:
                return to_int(read_data[DATA_BIT])
            except TypeError as e:
                print e
                continue
        raise SerialReadError

    def scrub(self):
        while self._read():
	    pass

class NasDateTime(object):

    dt_format = '%y-%m-%d %H:%M:%S'

    def __init__(self, serial_connection):
        self._ser = serial_connection

    def _parse_dt(self, data):
        dt_dict = {
                'year':  to_int(data[11]),
                'month': to_int(data[10]),
                'day':   to_int(data[9]),
                'h': to_int(data[7]), 'min': to_int(data[6]), 'sec': to_int(data[5]) }
        dt_str = '%(year)02i-%(month)02i-%(day)02i %(h)02i:%(min)02i:%(sec)02i' % dt_dict
        return datetime.strptime(dt_str, self.dt_format).replace(tzinfo=tz.tzutc())

    def _set_sys(self, dtime):
        dt_str = dtime.strftime(self.dt_format)
        os.system('date +\"%s\" -s \"%s\" > /dev/null' % (self.dt_format, dt_str))

    def getDateTime(self, set_sys=False):
        """
        set value: \xfa\x01\x08\x01\x01\x00\xfb (RDateAndTimeCmd)
        read data: \xfa\x01\x08\x01\x010#\x10\x00(\x06\x15\xfb'

        bit values 5 to 12:
            5: 30 ('0') second
            6: 23 ('#') minute
            7: 10 ('\x10') hour
            8: 0 ('\x00') -
            9: 28 ('(') date
            10: 6 ('\x06') month
            11: 15 ('\x15') year
            12: 161 ('\xfb') -

        .. _note:: time is in UTC
        """
        self._ser.scrub()
        self._ser.write(RDateAndTimeCmd)
        d = self._ser._read(size=13)
        if self._ser._debug: print 'read data: ' + repr(d)

        dt_utc = None
        retry = 0
        while dt_utc is None:
            try:
                dt_utc = self._parse_dt(d)
            except ValueError, e:
                if retry >= 3:
                    raise e
                else:
                    time.sleep(3); pass
            retry += 1

        dt = localTZ(dt_utc)
        if set_sys:
            self._set_sys(dt)
        return dt

    def setDateTime(self, set_dt=None):
        """
        see format getDateTime
        """
        if not set_dt:
            set_dt = datetime.now()
        set_dt_utc = localTZ(set_dt).astimezone(tz.tzutc())

        cmd = list(WDateAndTimeCmd)
        toHex = lambda form: to_hex_base8(int(set_dt_utc.strftime(form)))

        cmd[11], cmd[10], cmd[9] = toHex('%y'), toHex('%m'), toHex('%d')
        cmd[7], cmd[6], cmd[5] = toHex('%H'), toHex('%M'), toHex('%S')
        cmd = ''.join(cmd)

        if self._ser._debug:
            print 'set date and time: %s' % self._parse_dt(cmd)
        self._ser.write(cmd, size=13)

class NasAlarm(object):

    alarm_format = '%d.%m. %H:%M'
    rtc_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self, serial_connection):
        self._ser = serial_connection

    def __str__(self):
        wakeup = self.getAlarm()
        if not wakeup:
            return 'no alarm time set'
        else:
            return wakeup.strftime(self.alarm_format)

    def getAlarm(self):
        alarm_datetime = None
        try:
            alarm_datetime = self._read_alarm()
        except AlarmDisabledException:
            return None
        else:
            return localTZ(alarm_datetime)

    def _read_alarm(self, retry=3):
        for _ in range(retry):
            self._ser.scrub()
            try:
                hour, minute = self.__getTime()
                month, date = self.__getDate()
            except SerialReadError:
                if self._ser._debug: print 'SerialReadError - retry'
                continue
            try:
                return datetime(datetime.now().year, month, date, hour, minute, tzinfo=tz.tzutc())
            except ValueError as e:
                if self._ser._debug: print e
                continue
        raise SerialReadError

    def __getDate(self):
        month = self._ser.set_and_get(RAlarmMonthCmd)
        date = self._ser.set_and_get(RAlarmDateCmd)
        if self._ser._debug: print 'month {0} date {1}'.format(month, date)

        if month + date == 0:
            raise AlarmDisabledException
        elif date == 0 or date > 31 or month == 0 or month > 12:
            raise SerialReadError
        else:
            return month, date

    def __getTime(self):
        minute = self._ser.set_and_get(RAlarmMinuteCmd)
        hour = self._ser.set_and_get(RAlarmHourCmd)
        if self._ser._debug: print "hour {0} minute {1}".format(hour, minute)
        return hour, minute

    def setAlarm(self, dtime, check=True):
        dtime = localTZ(dtime).astimezone(tz.tzutc())

        self._ser.scrub()

        success = self.__setTime(dtime.hour, dtime.minute)
        success &= self.__setDate(dtime.month, dtime.day)
        self.__enableAlarm()

        if check: self.__checkAlarm(dtime)
        return success

    def disableAlarm(self):
        success = self.__setTime(0, 0)
        success &= self.__setDate(0, 0)
        self.__disableAlarm()
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
        setTime = localTZ(dtime).strftime(self.alarm_format)

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

    print 'current time: ' + datetime.now().strftime(NasAlarm.alarm_format)

    ser = SerialConnection()
    alarm = NasAlarm(ser)

    print 'old wakeup time: ' + str(alarm)

    wakeup = datetime.now() + timedelta(minutes=3)
    alarm.setAlarm(wakeup)

    print 'new wakup time: ' + wakeup.strftime(NasAlarm.alarm_format)
