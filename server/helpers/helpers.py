import json
import sys

import traceback

from opentrons.json_importer import JSONProtocolProcessor
from opentrons import robot, containers, instruments


JSON_ERROR = None
if sys.version_info > (3, 4):
    JSON_ERROR = ValueError
else:
    JSON_ERROR = json.decoder.JSONDecodeError


def get_frozen_root():
    """
    :return: Returns app path when app is packaged by pyInstaller
    """
    return sys._MEIPASS if getattr(sys, 'frozen', False) else None


def load_json(json_byte_stream):
    global robot
    json_str = _convert_byte_stream_to_str(json_byte_stream)

    api_response = {'errors': None, 'warnings': []}

    robot.reset()

    jpp = None
    errors, warnings = [], []
    try:
        jpp = JSONProtocolProcessor(json_str)
        jpp.process()
        robot.simulate()
    except JSON_ERROR:
        errors.append('Cannot parse invalid JSON')
    except Exception as e:
        errors.append(str(e))

    if jpp:
        errors.extend(jpp.errors)
        warnings.extend(jpp.warnings)

    if robot.get_warnings():
        warnings.extend(robot.get_warnings())

    api_response['errors'] = errors
    api_response['warnings'] = warnings
    return api_response


def load_python(stream, filename):
    global robot
    code = _convert_byte_stream_to_str(stream)
    api_response = {'errors': [], 'warnings': []}

    robot.reset()

    restore_patched_robot = _get_upload_proof_robot()
    try:
        try:
            exec(code, globals(), _get_protocol_locals())
        except Exception as e:
            tb = e.__traceback__
            stack_list = traceback.extract_tb(tb)
            _, line, name, text = stack_list[-1]
            if 'exec' in text:
                text = None
            raise Exception(
                'Error in protocol file line {} : {}\n{}'.format(
                    line,
                    str(e),
                    text or ''
                )
            )

        restore_patched_robot()
        robot.simulate()
    except Exception as e:
        api_response['errors'] = [str(e)]
    finally:
        restore_patched_robot()

    api_response['warnings'] = robot.get_warnings() or []

    return api_response


current_protocol_step_list = None


def create_step_list():
    global current_protocol_step_list
    current_protocol_step_list = [{
        'axis': instrument.axis,
        'label': instrument.name,
        'channels': instrument.channels,
        'placeables': [
            {
                'type': container.properties['type'],
                'label': container.get_name(),
                'slot': container.get_parent().get_name()
            }
            for container in _get_unique_containers(instrument)
        ]
    } for instrument in _get_all_pipettes()]

    return update_step_list()


def update_step_list():
    global current_protocol_step_list
    if not current_protocol_step_list:
        create_step_list()
    for step in current_protocol_step_list:
        _, instrument = robot.get_instruments_by_name(step['label'])[0]
        step.update({
            'top': instrument.positions['top'],
            'bottom': instrument.positions['bottom'],
            'blow_out': instrument.positions['blow_out'],
            'drop_tip': instrument.positions['drop_tip'],
            'max_volume': instrument.max_volume,
            'calibrated': _check_if_instrument_calibrated(instrument)
        })

        for placeable_step in step['placeables']:
            c = _get_container_from_step(placeable_step)
            if c:
                placeable_step.update({
                    'calibrated': _check_if_calibrated(instrument, c)
                })

    return current_protocol_step_list


def calibrate_placeable(container_name, axis_name):

    deck = robot._deck
    containers = deck.containers()
    axis_name = axis_name.upper()

    if container_name not in containers:
        raise ValueError('Container {} is not defined'.format(container_name))

    if axis_name not in robot._instruments:
        raise ValueError('Axis {} is not initialized'.format(axis_name))

    instrument = robot._instruments[axis_name]
    container = containers[container_name]

    well = container[0]
    pos = well.from_center(x=0, y=0, z=-1, reference=container)
    location = (container, pos)

    instrument.calibrate_position(location)
    return instrument.calibration_data


def calibrate_plunger(position, axis_name):
    axis_name = axis_name.upper()
    if axis_name not in robot._instruments:
        raise ValueError('Axis {} is not initialized'.format(axis_name))

    instrument = robot._instruments[axis_name]
    if position not in instrument.positions:
        raise ValueError('Position {} is not on the plunger'.format(position))

    instrument.calibrate(position)


def _convert_byte_stream_to_str(stream):
    return ''.join([line.decode() for line in stream])


def _get_protocol_locals():
    from opentrons import robot, containers, instruments  # NOQA
    return locals()


def _get_upload_proof_robot():
    methods_to_stash = [
        'connect',
        'disconnect',
        'move_head',
        'move_plunger',
        'reset',
        'run',
        'simulate'
    ]

    def mock(self, *args, **kwargs):
        pass

    stashed_methods = {}
    for method in methods_to_stash:
        stashed_methods[method] = getattr(robot, method)
        setattr(robot, method, mock)

    def restore():
        for method_name, method_obj in stashed_methods.items():
            setattr(robot, method_name, method_obj)

    return restore


def _sort_containers(container_list):
    """
    Returns the passed container list, sorted with tipracks first
    then alphabetically by name
    """
    _tipracks = []
    _other = []
    for c in container_list:
        _type = c.properties['type'].lower()
        if 'tip' in _type:
            _tipracks.append(c)
        else:
            _other.append(c)

    _tipracks = sorted(
        _tipracks,
        key=lambda c: c.get_name().lower()
    )
    _other = sorted(
        _other,
        key=lambda c: c.get_name().lower()
    )

    return _tipracks + _other


def _get_all_pipettes():
    global robot
    pipette_list = []
    for _, p in robot.get_instruments():
        if isinstance(p, instruments.Pipette):
            pipette_list.append(p)
    return sorted(
        pipette_list,
        key=lambda p: p.name.lower()
    )


def _get_all_containers():
    """
    Returns all containers currently on the deck
    """
    all_containers = list()
    global robot
    for slot in robot._deck:
        if slot.has_children():
            all_containers += slot.get_children_list()

    return _sort_containers(all_containers)


def _get_unique_containers(instrument):
    """
    Returns all associated containers for an instrument
    """
    unique_containers = set()
    for location in instrument.placeables:
        container_instances = [c for c in location.get_trace() if isinstance(
            c, containers.Container)]
        unique_containers.add(container_instances[0])

    return _sort_containers(list(unique_containers))


def _check_if_calibrated(instrument, container):
    """
    Returns True if instrument holds calibration data for a Container
    """
    slot = container.get_parent().get_name()
    label = container.get_name()
    data = instrument.calibration_data
    if slot in data:
        if label in data[slot].get('children'):
            return True
    return False


def _check_if_instrument_calibrated(instrument):
    # TODO: rethink calibrating instruments other than Pipette
    if not isinstance(instrument, instruments.Pipette):
        return True

    positions = instrument.positions
    for p in positions:
        if positions.get(p) is None:
            return False

    return True


def _get_container_from_step(step):
    """
    Retruns the matching Container for a given placeable step in the step-list
    """
    all_containers = _get_all_containers()
    for container in all_containers:
        match = [
            container.get_name() == step['label'],
            container.get_parent().get_name() == step['slot'],
            container.properties['type'] == step['type']

        ]
        if all(match):
            return container
    return None
