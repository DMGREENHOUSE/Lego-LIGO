#!/usr/bin/env python
# Dexter Industries
# Initial Date: June    24, 2013
# Updated: 	 August  13, 2014
# Updated:      Oct     28, 2016 Shoban
#
# These files have been made available online through a Creative Commons Attribution-ShareAlike 3.0  license.
# (http://creativecommons.org/licenses/by-sa/3.0/)
#
# This code is for testing the BrickPi with a Lego Motor.
# Connect the LEGO Motors to Motor ports MA,MB, MC and MD.
#
# You can learn more about BrickPi here:  http://www.dexterindustries.com/BrickPi
# Have a question about this example?  Ask on the forums here:  http://forum.dexterindustries.com/c/brickpi

#For the code to work - sudo pip install -U future

from __future__ import print_function
from __future__ import division
from builtins import input

# the above lines are meant for Python3 compatibility.
# they force the use of Python3 functionality for print(), 
# the integer division and input()
# mind your parentheses!

from BrickPi import *   #import BrickPi.py file to use BrickPi operations
import time
from time import sleep
import numpy as np
BrickPiSetup()  # setup the serial port for communication

BrickPi.MotorEnable[PORT_A] = 1 #Enable the Motor A
BrickPi.MotorEnable[PORT_B] = 1 #Enable the Motor B
BrickPi.MotorEnable[PORT_C] = 1 #Enable the Motor C
BrickPi.MotorEnable[PORT_D] = 1 #Enable the Motor D
"""
BrickPiSetupSensors()   #Send the properties of sensors to BrickPi
BrickPiUpdateValues()
motorRotateDegree([50], [0], [PORT_A])
BrickPiUpdateValues()
BrickPiSetupSensors()
print('finished')
"""
def motor(ti, speed):
    st = time.time()
    t = ti
    sp = int(round(speed))
    print(t, sp)
    while time.time() - st < t:
        BrickPi.MotorSpeed[PORT_B] =  sp
        BrickPiUpdateValues()
        while t + 0.05> time.time() - st >= t:
            BrickPi.MotorSpeed[PORT_B] =  0
            BrickPiUpdateValues()
a = [1, 0.5, 1, 1.25, 0.7, 1.3, 0.5]
b = [20, -20, -40, 40, -30, 20, -20]
#a = np.array([1, 1, 1])
#b = np.array([20, -20, 20])
c = np.c_[a, b]
print(c)
count = 0
for i in b:
    motor(a[count], i)
    count += 1
"""
while True:
    print("Running")
    BrickPi.MotorSpeed[PORT_A] =  50
    BrickPiUpdateValues()
"""
"""
while True:
    print ("Running Forward")
    power = 0
    BrickPi.MotorSpeed[PORT_A] = power  #Set the speed of MotorA (-255 to 255)
    BrickPi.MotorSpeed[PORT_B] = power  #Set the speed of MotorB (-255 to 255)
    BrickPi.MotorSpeed[PORT_C] = power  #Set the speed of MotorC (-255 to 255)
    BrickPi.MotorSpeed[PORT_D] = power  #Set the speed of MotorD (-255 to 255)

    ot = time.time()
    while(time.time() - ot < 3):    #running while loop for 3 seconds
        BrickPiUpdateValues()       # Ask BrickPi to update values for sensors/motors
    time.sleep(.1)

    print ("Running Backward")
    power = -50
    BrickPi.MotorSpeed[PORT_A] = power  #Set the speed of MotorA (-255 to 255)
    BrickPi.MotorSpeed[PORT_B] = power  #Set the speed of MotorB (-255 to 255)
    BrickPi.MotorSpeed[PORT_C] = power  #Set the speed of MotorC (-255 to 255)
    BrickPi.MotorSpeed[PORT_D] = power  #Set the speed of MotorD (-255 to 255)

    ot = time.time()
    while(time.time() - ot < 3):    #running while loop for 3 seconds
        BrickPiUpdateValues()       # Ask BrickPi to update values for sensors/motors
        time.sleep(.1)              # sleep for 100 ms
"""
