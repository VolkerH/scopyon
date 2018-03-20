import os.path
import csv
import copy
from ast import literal_eval
from collections import namedtuple

import numpy

from logging import getLogger
_log = getLogger(__name__)


def read_spatiocyte(pathto, tstart, tend, exposure_time, observable=None, max_count=None):
    (interval, species_id, lengths, voxel_radius, observables) = read_spatiocyte_input(os.path.join(pathto, 'pt-input.csv'), observable)
    (count_array, index_array_size, index0, time_array, delta_array, count_array) = spatiocyte_time_arrays(tstart, tend, interval, exposure_time)
    data = read_spatiocyte_data(pathto, count_array, species_id=species_id, observables=observables, max_count=max_count)
    assert len(count_array) == len(data)

    SpatiocyteDataSet = namedtuple('SpatiocyteDataSet', ('data', 'index_array_size', 'index0', 'interval', 'lengths', 'voxel_radius', 'time_array', 'delta_array'))
    return SpatiocyteDataSet(data, index_array_size=index_array_size, index0=index0, interval=interval, lengths=lengths, voxel_radius=voxel_radius, time_array=time_array, delta_array=delta_array)

def spatiocyte_time_arrays(start_time, end_time, interval, exposure_time):
    # set count arrays by spatiocyte interval
    N_count = int(round((end_time - start_time) / interval))
    c0 = int(round(start_time / interval))

    delta_array = numpy.zeros(shape=(N_count))
    delta_array.fill(interval)
    time_array  = numpy.cumsum(delta_array) + start_time
    count_array = numpy.array([c + c0 for c in range(N_count)])

    # set index arrays by exposure time
    N_index = int(round((end_time - start_time) / exposure_time))
    i0 = int(round(start_time / exposure_time))
    index_array = numpy.array([i + i0 for i in range(N_index)])

    return (count_array, len(index_array), index_array[0], time_array, delta_array, count_array)

def read_spatiocyte_input(filename, observable=None):
    with open(filename, 'r') as f:
        header = f.readline().rstrip().split(',')

    header[:5] = [float(_) for _ in header[:5]]
    interval, lengths, voxel_r, species_info = header[0], (header[3:0:-1]), header[4], header[5:]

    species_id = range(len(species_info)-2)
    species_index  = [_.split(':')[1].split(']')[0] for _ in species_info[0:len(species_info)-2]]
    species_radius = [float(_.split('=')[1]) for _ in species_info[0:len(species_info)-2]]

    # set observable
    if observable is None:
        index = [True for i in range(len(species_index))]
    else:
        index = list(map(lambda x:  True if x.find(observable) > -1 else False, species_index))

    _log.info('    Time Interval = {} sec'.format(interval))
    _log.info('    Voxel radius  = {} m'.format(voxel_r))
    _log.info('    Compartment lengths: {} voxels'.format(lengths))
    _log.info('    Species Index: {}'.format(species_index))
    _log.info('    Observable: {}'.format(index))

    return (interval, species_id, lengths, voxel_r, copy.copy(index))

def read_spatiocyte_shape(filename):
    cell_shape = numpy.genfromtxt(filename, delimiter=',')
    cell_shape = numpy.array(cell_shape.tolist())  #XXX: == cell_shape?
    return cell_shape

def read_spatiocyte_data(pathto, count_array=None, species_id=None, observables=None, max_count=None):
    species_id = numpy.array(species_id)

    # set data-array
    data = []

    # read lattice file
    for i in range(len(count_array)):
        csv_file_path = os.path.join(pathto, 'pt-{:09d}.0.csv'.format(count_array[i]))
        if not os.path.isfile(csv_file_path):
            # _log.err('{} not found'.format(csv_file_path))
            raise RuntimeError('File [{}] was not found'.format(csv_file_path))

        with open(csv_file_path, 'r') as csv_file:
            particles = []
            t = None
            for row in csv.reader(csv_file):
                t_ = float(row[0])
                coordinate = (float(row[1]), float(row[2]), float(row[3]))
                # radius = float(row[4])
                # Molecule ID and its state
                id1 = literal_eval(row[5])
                assert isinstance(id1, tuple) and len(id1) == 2
                # Fluorophore ID and compartment ID
                id2 = literal_eval(row[6])
                assert isinstance(id2, tuple) and len(id2) == 2

                if len(row) >= 9:
                    p_state, cyc_id = float(row[7]), float(row[8])
                else:
                    p_state, cyc_id = 1.0, float('inf')

                s_index = (numpy.abs(species_id - int(id1[1]))).argmin()
                if observables[s_index] is True:
                    particles.append((coordinate, id1[0], id1[1], id2[1], p_state, cyc_id))

                if t is None:
                    t = t_
                elif t != t_:
                    raise RuntimeError('File [{}] contains multiple time'.format(csv_file_path))

        # Just for debugging
        if max_count is not None and len(particles) > max_count:
            particles = particles[: max_count]

        _log.debug('File [{}] was loaded. [t={}, #particles={}]'.format(csv_file_path, t, len(particles)))
        data.append([t, particles])

    # data.sort(key=lambda x: x[0])
    return data
