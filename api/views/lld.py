"""For low level discovery in Zabbix"""
import string

import flask

from api import app
from api.json_handler import get_lld_sensors


def filter_str_sensors(filter_args: str, sensor_key: str, sensors: list) -> list[dict]:
    """Filter LLD JSON with data like hardware names."""
    filter_args = filter_args.lower()
    filtered_sensors_usual = []
    filtered_sensors_not = []

    if filter_args:
        for argument in filter_args.split(','):
            for sensor in sensors:
                if argument[0:4] == 'not_':
                    if argument[4:] in sensor[sensor_key].lower():
                        filtered_sensors_not.append(sensor)
                    else:
                        filtered_sensors_usual.append(sensor)
                if '_any_' in argument:
                    for _any_ in string.printable:
                        if argument.replace('_any_', _any_) in sensor[sensor_key].lower():
                            filtered_sensors_usual.append(sensor)
                if argument in sensor[sensor_key].lower():
                    filtered_sensors_usual.append(sensor)

        filtered_sensors_usual = set(tuple(sensor.items()) for sensor in filtered_sensors_usual)
        filtered_sensors_not = set(tuple(sensor.items()) for sensor in filtered_sensors_not)

        filtered_sensors = filtered_sensors_usual - filtered_sensors_not
        filtered_sensors_list = [dict(sensor_set) for sensor_set in filtered_sensors]

        return filtered_sensors_list
    return sensors


def filter_int_sensors(filter_args: str, sensor_key: str, sensors: list) -> list[dict]:
    """Filter LLD JSON with data like hardware names."""
    filter_args = filter_args.lower().strip().replace(' ', '')
    filter_args_one = []
    filter_args_range = []
    filtered_sensors = []

    if filter_args:
        for arg in filter_args.split(','):
            if '-' in arg:
                filter_args_range.append(arg)
            else:
                filter_args_one.append(arg)

        filter_args_one = [int(value) for value in filter_args_one]
        filter_args_range = [[int(value) for value in arg.split('-')] for arg in filter_args_range]

        for sensor in sensors:
            if sensor[sensor_key] in filter_args_one:
                filtered_sensors.append(sensor)

            for arg_range in filter_args_range:
                for sensor_index_arg in range(arg_range[0], arg_range[-1] + 1):
                    if sensor[sensor_key] == sensor_index_arg:
                        filtered_sensors.append(sensor)

        return filtered_sensors
    return sensors


@app.route("/hardware_lld", methods=['GET'])
def scan_hardware_lld():
    """
Get json for LLD discovery and filter with queries.
    All type: query
    All Default: ''

    hardware_name:
            Options: GPU, CPU, NOT_GPU, System, etc...

    hardware_index:
            Options: Singe value: 1; Array: 0,1,2,6,10; Range: 1-10, Ranges: 1-3,5-8 etc...

    sensor_name:
            Options: core _any_ vid, Used, not_gpu etc...

    sensor_index:
            Options: See hardware_index

    sensor_type_name:
            Options: None, Temp, Voltage, Fan, Current, Power, Clock, Usage, Other

    sensor_type_index:
            Options: See hardware_index

    unit:
            Options: '',°C, RPM, MB,  NOT_MB, GB, KB/s, MB/s, GT/s, , %, x, T, Yes/No, Gbps etc...

Examples:

RAM Clock:\t http://127.0.0.1:50000/hardware_lld?hardware_name=Memory%20Timings&sensor_name=Memory%20Clock&sensor_type_name=Clock&unit=mhz
RAM timings:\t http://127.0.0.1:50000/hardware_lld?hardware_name=Memory%20Timings&sensor_name=&unit=T
All core VIDs:\t http://127.0.0.1:50000/hardware_lld?sensor_name=Core%20_any_%20VID
CPU Temp:\t http://127.0.0.1:50000/hardware_lld?sensor_name=CPU%20_any_Tctl&sensor_type_name=Temp&unit=%C2%B0C
CPU Temps:\t http://127.0.0.1:50000/hardware_lld?sensor_name=tctl,cpu,not_aver,not_gpu,not_drive,not_system,not_core,not_cache,not_pch,not_vr%20mos,not_peci,not_ccd1,not_hotspot&sensor_type_name=Temp&unit=%C2%B0C
GPU Temps:\t http://127.0.0.1:50000/hardware_lld?sensor_name=GPU&sensor_type_name=Temp&unit=%C2%B0C
Motherboard Temps:\t http://127.0.0.1:50000/hardware_lld?hardware_name=nuvoton&sensor_name=not_cpu&sensor_type_name=temp
CPU,GPU Powers:\t http://127.0.0.1:50000/hardware_lld?sensor_name=CPU%20Package%20Power,GPU%20Power%20_any_Total,GPU%208-pin,GPU%20PCIe&sensor_type_name=Power&unit=W
GPU Fans:\t http://127.0.0.1:50000/hardware_lld?sensor_name=GPU&sensor_type_name=Fan&unit=RPM
GPU Powers:\t http://127.0.0.1:50000/hardware_lld?sensor_name=GPU%20Power%20_any_Total%2CGPU%208-pin%2CGPU%20PCIe&sensor_type_name=Power&unit=W
"""

    hardware_name = flask.request.args.get('hardware_name', default='', type=str)
    hardware_index = flask.request.args.get('hardware_index', default='', type=str)
    sensor_name = flask.request.args.get('sensor_name', default='', type=str)
    sensor_index = flask.request.args.get('sensor_index', default='', type=str)
    sensor_type_name = flask.request.args.get('sensor_type_name', default='', type=str)
    sensor_type_index = flask.request.args.get('sensor_type_index', default='', type=str)
    unit = flask.request.args.get('unit', default='', type=str)

    sensors = get_lld_sensors()

    sensors = filter_str_sensors(hardware_name, '{#HARDWARENAME}', sensors)
    sensors = filter_str_sensors(sensor_name, '{#SENSORNAME}', sensors)
    sensors = filter_str_sensors(sensor_type_name, '{#SENSORTYPENAME}', sensors)
    sensors = filter_str_sensors(unit, '{#UNIT}', sensors)

    sensors = filter_int_sensors(hardware_index, '{#HARDWAREINDEX}', sensors)
    sensors = filter_int_sensors(sensor_index, '{#SENSORINDEX}', sensors)
    sensors = filter_int_sensors(sensor_type_index, '{#SENSORTYPEINDEX}', sensors)

    sensors_set = [dict(s) for s in set(tuple(sensor.items()) for sensor in sensors)]
    sensors_sorted = sorted(sensors_set, key=lambda key: (key['{#SENSORINDEX}']))

    return flask.jsonify(sensors_sorted)


@app.route("/value_lld/<sensor_index>")
def get_value_lld(sensor_index: str):
    # noinspection HttpUrlsUsage
    """Get value by sensor_index
    sensor_index: sensor number from range 0 till end
            Type: path parameter

    debug: show the context for a value
            Type: query
            Options: true, false
            Default: false

    Examples:
    http://127.0.0.1:50000/value_lld/189
    http://127.0.0.1:50000/value_lld/155?debug=true
    """
    sensor_index = int(sensor_index)
    debug = flask.request.args.get('debug', default="false", type=str)

    sensors = get_lld_sensors()

    if debug.lower() == "true":
        return flask.jsonify(sensors[sensor_index])

    return flask.jsonify(sensors[sensor_index]["{#VALUE}"])
