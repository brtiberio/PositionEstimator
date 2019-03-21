#!/usr/bin/python
# -*- coding: utf-8 -*-
# The MIT License (MIT)
# Copyright (c) 2018 Bruno Tibério
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import threading
import os
import pymap3d

from novatel_OEM4_python.NovatelOEM4 import Gps



try:
    import queue
except ImportError:
    import Queue as queue

from time import sleep
import signal
import logging

def saveGpsData(dataQueue, fileFP, exitFlag):
    fileFP.write(
        "Indice,Time,PSolStatus,X,Y,Z,stdX,stdY,stdZ,VSolStatus,VX,VY,VZ,stdVX,stdVY,stdVZ,VLatency,SolAge,SolSatNumber\n")
    fileFP.flush()
    while(exitFlag.isSet() == False):
        if(dataQueue.empty() == False):
            newData = dataQueue.get()
            fileFP.write('{0:5d},{1},{2},{3},{4},{5},'
                         '{6},{7},{8},{9},{10},{11},'
                         '{12},{13},{14},{15},{16},'
                         '{17},{18}\n'.format(newData['Indice'],
                                              newData['Time'],
                                              newData['pSolStatus'],
                                              newData['position'][0],
                                              newData['position'][1],
                                              newData['position'][2],
                                              newData['positionStd'][0],
                                              newData['positionStd'][1],
                                              newData['positionStd'][2],
                                              newData['velSolStatus'],
                                              newData['velocity'][0],
                                              newData['velocity'][1],
                                              newData['velocity'][2],
                                              newData['velocityStd'][0],
                                              newData['velocityStd'][1],
                                              newData['velocityStd'][2],
                                              newData['vLatency'],
                                              newData['solAge'],
                                              newData['numSolSatVs']
                                              ))
            fileFP.flush()
        else:
            sleep(0.1)
    return


# def saveRazorData(dataQueue, fileFP, exitFlag):
#     fileFP.write(
#         "Index,Time,ID,accx,accy,accz,gyrox,gyroy,gyroz,magx,magy,magz,yaw,pitch,roll\n")
#     fileFP.flush()
#     while(exitFlag.isSet() == False):
#         if(dataQueue.empty() == False):
#             newData = dataQueue.get()
#             fileFP.write('{0:5d},{1},{2},{3:.2f},{4:.2f},{5:.2f},{6:.2f},'
#                          '{7:.2f},{8:.2f},{9:.2f},{10:.2f},{11:.2f},'
#                          '{12:.2f},{13:.2f},{14:.2f}'
#                          '\n'.format(newData['Indice'],
#                                      newData['Time'],
#                                      newData['ID'],
#                                      newData['Acc'][0],
#                                      newData['Acc'][1],
#                                      newData['Acc'][2],
#                                      newData['Gyro'][0],
#                                      newData['Gyro'][1],
#                                      newData['Gyro'][2],
#                                      newData['Mag'][0],
#                                      newData['Mag'][1],
#                                      newData['Mag'][2],
#                                      newData['euler'][0],
#                                      newData['euler'][1],
#                                      newData['euler'][2]
#                                      ))
#             fileFP.flush()
#         else:
#             sleep(0.01)
#     return

def main():
    """
    :return:
    """
    def signal_handler(signal, frame):
        print('You pressed Ctrl+C!')
        # razor.shutdown()
        gps1.shutdown()
        gps2.shutdown()
        return

    def clean_exit():
        logging.info("Requesting clean exit...")
        gps1.shutdown()
        gps2.shutdown()
        # razor.shutdown()
        exit_flag.set()
        # razorThreads[0].join()
        gps_threads[0].join()
        gps_threads[1].join()
        logging.info("Successfully exited from devices")
        return

    # --------------------------------------------------------------------------
    #
    # Start of main part
    #
    # --------------------------------------------------------------------------

    parser = argparse.ArgumentParser(add_help=True, description="Logger for two GPS units and a razor device")
    parser.add_argument("--gps1-port", action="store", type=str,
                        dest="gps1_port", default="/dev/ttyUSB0")
    parser.add_argument("--gps2-port", action="store", type=str,
                        dest="gps2_port", default="/dev/ttyUSB1")
    parser.add_argument("-f", "--folder", action="store", type=str,
                        dest="folder", default="test1")
    parser.add_argument('--log', action='store', type=str, dest='log', default='main.log',
                        help='log file to be used')
    parser.add_argument("--log-level", action="store", type=str,
                        dest="logLevel", default='info',
                        help='Log level to be used. See logging module for more info',
                        choices=['critical', 'error', 'warning', 'info', 'debug'])
    args = parser.parse_args()

    log_level = {'error': logging.ERROR,
                 'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'warning': logging.WARNING,
                 'critical': logging.CRITICAL
                 }
    # --------------------------------------------------------------------
    # create folder anc change dir
    # --------------------------------------------------------------------
    os.chdir('..')
    current_dir = os.getcwd()
    current_dir = current_dir + "/data/" + args.folder
    if not os.path.exists(current_dir):
        os.makedirs(current_dir)
    os.chdir(current_dir)
    # --------------------------------------------------------------------
    logging.basicConfig(filename=args.log,
                        level=log_level[args.logLevel],
                        format='[%(asctime)s] [%(name)-20s] [%(threadName)-10s] %(levelname)-8s %(message)s',
                        filemode="w")

    # ---------------------------------------------------------------------------
    # define a Handler which writes INFO messages or higher in console
    # ---------------------------------------------------------------------------
    console = logging.StreamHandler()
    console.setLevel(log_level[args.logLevel])
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-20s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    # event flag to exit
    exit_flag = threading.Event()

    # create classes for sensors
    gps1 = Gps("GPS1")
    gps2 = Gps("GPS2")

    # create Thread pointers
    gps_threads = [0] * 2

    # create inter threads fifos
    gps1_fifo = queue.Queue()
    gps2_fifo = queue.Queue()

    # open files for storing data from sensors
    gps1_fp = open('gps1.csv', 'w')
    gps2_fp = open('gps2.csv', 'w')

    # declare threads
    gps_threads[0] = threading.Thread(name="gps1", target=saveGpsData,
                                      args=(gps1_fifo, gps1_fp, exit_flag))
    gps_threads[1] = threading.Thread(name="gps2", target=saveGpsData,
                                      args=(gps2_fifo, gps2_fp, exit_flag))

    if gps1.begin(gps1_fifo, comPort=args.gps1_port) != 1:
        logging.info("Not able to begin device properly... check logfile")
        return
    if gps2.begin(gps2_fifo, comPort=args.gps2_port) != 1:
        logging.info("Not able to begin device properly... check logfile")
        return

    # start threads
    gps_threads[0].start()
    gps_threads[1].start()
    # prepare signal and handlers
    signal.signal(signal.SIGINT, signal_handler)

    # send unlogall
    if gps1.sendUnlogall() != 1:
        logging.info("Unlogall command failed on gps1... check logfile")
        clean_exit()
        logging.shutdown()
        logging.info('Exiting now')
        return
    # send unlogall
    if gps2.sendUnlogall() != 1:
        logging.info("Unlogall command failed on gps2... check logfile")
        clean_exit()
        return

    # reconfigure port
    gps1.setCom(baud=115200)
    gps2.setCom(baud=115200)

    # set dynamics [0 air, 1 land, 2 foot]
    gps1.setDynamics(0)
    gps2.setDynamics(0)

    # enable augmented satellite systems
    gps1.sbascontrol()
    gps2.sbascontrol()

    # ask for bestxyz log at 20Hz
    gps1.askLog(trigger=2, period=0.05)
    gps2.askLog(trigger=2, period=0.05)
    # wait for Ctrl-C
    logging.info('Press Ctrl+C to Exit')
    signal.pause()
    clean_exit()
    logging.shutdown()
    logging.info('Exiting now')


if __name__ == '__main__':
    main()

