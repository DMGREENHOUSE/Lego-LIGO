# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 17:00:00 2017

author:
    Daniel Greenhouse,
    University of Birmingham
"""

#for the BrickPi code to work - sudo pip install -U future
#below lines are for Python3 compatibility
from __future__ import print_function
from __future__ import division
from builtins import input

"""
Section 1: Choices for how the program should executed.
    RP:
        Used for easy changing between the Raspberry Pi Version and an alternative
            version used by an editor.
        The editor should enter their folder directory in IMAGE_LOCATION and PARAMS of section 3 as
            well as sections 9 and 15a.
    Stationary_points:
        Used for easy changing of the motor mode.
        Stationary_points finds the peaks and troughs of the wave and runs to that
            position, while the alternative (time spacing) finds where the motor
            should be every x seconds (specified in 'data_point_spacing' of PARAMS,
            section()) and runs to that position.
    True executes the specified version.
"""
#platform
RP = True
#output
Stationary_points = True

"""
Section 2: import modules to be used. Prints to let the user know why the GUI is
    taking time to load.
"""
print('Loading Modules...')
import sys
import os
import matplotlib
import time
from time import sleep
import numpy as np
try:
    from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QSizePolicy, QMainWindow
    from PyQt5.QtGui import QIcon, QImage, QPalette, QBrush, QPixmap
    from PyQt5.QtCore import QSize, Qt
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from PyQt4.QtGui import QApplication, QMainWindow, QPushButton, QWidget, QLabel
    from PyQt4.QtGui import QIcon, QImage, QPalette, QBrush, QSizePolicy, QPixmap
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from PyQt4.QtCore import QSize, Qt
    matplotlib.use('Qt4Agg')

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

try:#checks BrickPi+
    from BrickPi import *
    BrickPiSetup() #setup the serial port for communication
    BrickPi.MotorEnable[PORT_B] = 1#enable ports
    BrickPi.MotorEnable[PORT_A] = 1#enable ports
    BrickPiSetupSensors() #Send the properties of sensors to BrickPi

except ImportError:
    pass

print('Modules Loaded.')

"""
Section 3: Global paramaters to be used throughout
"""
global MXPos
global MYPos
MXPos = 0 #Mirror A degree position
MYPos = 0 #Mirror B degree position
#relays output chosen in section 1
if Stationary_points is True:
    mode = 'motor_stationary_points'
if Stationary_points is False:
    mode = 'time_spacing'

if RP is True:
    IMAGE_LOCATION = r'/home/pi/Documents/LEGO_LIGO/Images'
else:
    IMAGE_LOCATION = r''#the editor should enter their image folder location here

PARAMS = {
    'FOLDER' : r'', #the editor should enter their test code folder location here
    #the test code folder location on the Raspberry Pi
    'RPFOLDER' : r'/home/pi/Documents/LEGO_LIGO/Test code',
    'COL_NAMES' :  ['Time [s]', 'Strain'], # list of column names (as in the file)
    'LINES_TO_SKIP' : 1,# lines to skip when reading data files
    'data_point_spacing' : 0.2, #desired time spacing of data points
    #speed of return to 0 degree mark, used when resetting mirror position in section 13
    'return_pwr' : 20,
    'degree_max' : 180, #greatest degree position from 0
    'time_scale' : 15, #time conversion multiplier from csv to motor and graph
    'self_movement_run_time' : 0.15, #motor forward, backward run time, in seconds, in self-movement mode
    'self_movement_pwr' : 30, #motor forward, backward power in self-movement mode
    'Calibrate_run_time' : 0.1, #motor forward, backward run time, in seconds, in calibrate mode
    'Calibrate_pwr' : 20,#motor forward, backward power in calibrate mode
    'pwrcoef' : 4.5, #pwrcoef = degree/(power*time)
    'presetbuffer' : 0.5, #to ensure motors don't over-run in preset mode, fraction out of 1
    'manualbuffer' : 0.8, #to ensure motors don't over-run in manual mode, fraction out of 1
    'stop_buffer': 0.02, #gives time to stop, in seconds
    'mode' : mode, #used for output in section 1
    #power multiplier for fast forward and fast rewind buttons in self-movement and calibrate mode
    'Fast_power_multiplier' : 2,
    #time multiplier for fast forward and fast rewind buttons in self-movement and calibrate mode
    'Fast_time_multiplier' : 3,
    }


def files_in_folder(folder_name):
    """
    Section 4:
        Loads csv files in the folder
        if "csv" ensures only csv files are given as an option

    Parameters
    --------
    folder_name = name of the test code folder

    Returns
    --------
    files = list of csv files only
    """
    load_files = os.listdir(folder_name) #folder_name passed into function
    files = [x for x in load_files if "csv" in x] #reduces load_files to csv files only
    return files

def read_csvfile_in_folder(folder_name, file_name):
    """
    Section 5: Reads the csv file

    Parameters
    ----------
    LINES_TO_SKIP = the lines taken up at the start by the column headers, defined in PARAMS
    folder_name = name of the test code folder
    file_name = relates to the name of the file to read

    Returns
    --------
    data = 2D array (2 columns), time in the first column and strain in the second column
    """
    data = np.loadtxt(folder_name+os.sep+file_name, delimiter=',',
                      skiprows=PARAMS['LINES_TO_SKIP'])
    return data

def degree_velocity(folder, file, type):
    """
    Section 6: Transforms the time, strain data for motor and graph to use
        type is to allow the function to be called by different functions and manipulate
             the data in the desired way


    Returns
    ----------
    dv_data = array of columns:times, velocity, degrees, degree differences, time differences and strain
    warning = if the motor cannot achieve the required power

    """
    old_data = read_csvfile_in_folder(folder, file) #call time, strain data

    #below: allows for original data to have -ve times
    time_total = (np.max(old_data[:, 0]) - np.min(old_data[:, 0]))*PARAMS['time_scale']
    i = int((len(old_data)*PARAMS['data_point_spacing'])/time_total) #rounds to 0 dp then integer
    if i > 0:
        new_data = old_data[0::i] #inculdes first data point
    elif i <= 0:
        new_data = old_data
    if type == 'time_spacing':
        data = new_data
    if type == 'all_points':
        data=old_data
    if type == 'motor_stationary_points':
        count = 0
        stptdata = []
        for i in range(0, (len(old_data[:, 1]) - 2)): #goes twice past to check both ways
            count += 1
            ths = old_data[:, 1][count]
            prv = old_data[:, 1][count-1]
            nxt = old_data[:, 1][count+1]
            if ((ths - prv > 0) and (nxt-ths < 0)) or ((ths-prv < 0) and (nxt-ths > 0)):
                stptdata.append([old_data[:, 0][count], old_data[:, 1][count]])
        data = np.asarray(stptdata)
    if type == 'warning_check':
        #only checks when in time_spacing mode
        data = new_data
    strain_diff = max(np.abs(data[:, 1])) - 0 #abs ensures both +ve and -ve values accounted for
    #below: degree_max/strain_diff is a scale factor for converting strain to degrees
    degrees = data[:, 1]*PARAMS['degree_max']*PARAMS['presetbuffer']/strain_diff
    #add 0 to beginning and removes final degree point:
    old_degrees = np.append(0, degrees[:(len(degrees) -1)])
    #below: corrects time array since usually time 0 is the merger
    times = (data[:, 0] - np.min(data[:, 0]))*PARAMS['time_scale']
    final_time_diff = times[len(times) - 1] - times[len(times) - 2] #final time difference
    #assumes new final time step is same as previous final:
    new_times = np.append(times[1:], (times[len(times) - 1] + final_time_diff))
    time_diff = new_times - times
    degree_diff = degrees - old_degrees
    velocity = (degrees - old_degrees)/(time_diff)
    strain = degrees/1800#approximately for LEGO LIGO

    dv_data = np.c_[times, velocity, degrees, degree_diff, time_diff, strain] #converts 4 columns to a numpy array
    warning = False
    if np.max(degrees - old_degrees) > 10000*PARAMS['data_point_spacing']: #coefficient is for motor speed limit
        warning = True
    return dv_data, warning

class Window():
    """Section 7: Class for describing the Widget Window dimensions, positioning and title"""
    title = 'LEGO-LIGO'#Widget title
    left = 0#window distance from left of screen
    top = -1#window distance from top of screen, fills Raspberry Pi 7" touchscreen
    if RP is True:
        width = 800#window width
        height = 480#window height
    else:
        width = 1600#window width
        height = 960#window height
    fnt10hght = height/28#used for setting label heights of certain font sizes
    fnt12hght = height/23#used for setting label heights of certain font sizes
    fnt14hght = height/20#used for setting label heights of certain font sizes
    fnt16hght = height/17#used for setting label heights of certain font sizes


class CreateButton():
    """Section 8: Class for setting button styles, the buttons are actually made in each UI class"""
    def homechoicestyle(self, buttonname, name, xposition):
        """Used for changing the appearance of square, image buttons on the home screen

        Parameters
        -----------
        buttonname = the name of the button being edited
        name = string, matches the saved .jpg image name
        xposition = float, used for x screen positioning
        yposition = float, used for y screen positioning
        home = boolean, used for differentiating between image buttons when setting tool tip
        """
        ystart = Window.height*3/5
        #scales button dimensions with window size, ensures square buttons
        buttonwidth = Window.width/8
        buttonheight = Window.width/8
        #used for seperating buttons, helps to scale when changing window size
        buttonxgap = Window.width/8
        #alters button appearance
        buttonname.setStyleSheet("background-color: rgba(0,0,0,0)")#sets a transparent background
        buttonname.setIcon(QIcon(IMAGE_LOCATION+os.sep+'{}.png'.format(name)))#loads image
        buttonname.setIconSize(QSize(buttonwidth, buttonheight))
        buttonname.setFixedSize(buttonwidth, buttonheight)
        #repositions buttons
        buttonname.move((Window.width - buttonwidth)/2 + buttonwidth*(xposition - 2) + buttonxgap*(xposition - 2),
                        ystart)
        buttonname.setToolTip("Enters '{}' Mode".format(name.replace('_', ' ')))

    def movechoicestyle(self, buttonname, name, xposition, yposition):
        """For the motor moving buttons
        Split into a grid.
        Width: 8 boxes of buttonwidth seperated by 7 boxes of buttonxgap
        Height: buttons start half way down the page"""
        buttonwidth = Window.width/9
        buttonxgap = Window.width/63
        buttonheight = Window.width/9
        buttonygap = Window.height/20
        ystart = Window.height/2
        #alters button appearance
        buttonname.setStyleSheet("background-color: rgba(0,0,0,0)")#sets a transparent background
        buttonname.setIcon(QIcon(IMAGE_LOCATION+os.sep+'{}.png'.format(name)))#loads image
        buttonname.setFixedSize(buttonwidth, buttonheight)
        buttonname.setIconSize(QSize(buttonwidth, buttonheight))
        buttonname.move(buttonxgap*xposition + buttonwidth*xposition,
                        ystart + buttonygap*(yposition - 1) + buttonheight*(yposition - 1))
        buttonname.setToolTip("{}".format(name.replace('_', ' ')))
    def namestyle(self, buttonname, yposition):
        """Used for changing the appearance of rectangular, text buttons.
        Places them in two columns
        """
        ystart = Window.height*3/10
        xstart = Window.width/12
        #scales button dimensions with window size, ensures square buttons
        buttonwidth = Window.width/3
        buttonheight = Window.height/9
        #used for seperating buttons, helps to scale when changing window size
        buttonygap = Window.height/45
        buttonxgap = Window.width/6
        #alters button appearance
        buttonname.setFixedSize(buttonwidth, buttonheight)
        if yposition <= 5:
            buttonname.move(xstart, ystart + buttonheight*(yposition - 1) + buttonygap*(yposition - 1))
        if yposition >= 6:
            buttonname.move(xstart + buttonwidth + buttonxgap, (ystart + buttonheight*(yposition - 6) + buttonygap*(yposition - 6)))
        #repositions buttons
    def nextstyle(self, buttonname):
        """For the next button"""
        buttonwidth = Window.height/8
        buttonheight = Window.height/8
        buttonname.setStyleSheet("background-color: rgba(0,0,0,0)")
        buttonname.setIcon(QIcon(IMAGE_LOCATION+os.sep+'Next.png'))
        buttonname.setIconSize(QSize(buttonwidth, buttonheight))
        buttonname.setFixedSize(buttonwidth, buttonheight)
        buttonname.move(Window.width*9/10, Window.height*32/40)
    def exitstyle(self, buttonname):
        """For the exit buton"""
        buttonwidth = Window.height/8
        buttonheight = Window.height/8
        buttonname.setStyleSheet("background-color: rgba(0,0,0,0)")
        buttonname.setIcon(QIcon(IMAGE_LOCATION+os.sep+'Exit.png'))
        buttonname.setIconSize(QSize(buttonwidth, buttonheight))
        buttonname.setFixedSize(buttonwidth, buttonheight)
        buttonname.move(Window.width*9/10, Window.height*1/40)
        buttonname.setToolTip("Exit Application")
    def homestyle(self, buttonname):
        """For the home button"""
        buttonwidth = Window.height/8
        buttonheight = Window.height/8
        buttonname.setStyleSheet("background-color: rgba(0,0,0,0)")
        buttonname.setIcon(QIcon(IMAGE_LOCATION+os.sep+'Home.png'))
        buttonname.setIconSize(QSize(buttonwidth, buttonheight))
        buttonname.setFixedSize(buttonwidth, buttonheight)
        buttonname.move(Window.width*9/10, Window.height*32/40)
        buttonname.setToolTip("Home")
    def tickstyle(self, buttonname):
        """for the set calibration button"""
        buttonwidth = Window.height/8
        buttonheight = Window.height/8
        buttonname.setStyleSheet("background-color: rgba(0,0,0,0)")
        buttonname.setIcon(QIcon(IMAGE_LOCATION+os.sep+'Set.png'))
        buttonname.setIconSize(QSize(buttonwidth, buttonheight))
        buttonname.setFixedSize(buttonwidth, buttonheight)
        buttonname.move(Window.width*8/10, Window.height*32/40)
        buttonname.setToolTip("Set Calibration")


class CreateLabel():
    """Section 9: Class for setting Label styles, the labels are actually made in each UI class.
                These correspond to the buttons in Section 10
    """
    def titlestyle(self, labelname):
        """For the LEGO LIGO Title image"""
        labelheight = Window.height/10
        labelwidth = labelheight*1243/254
        if RP is True:
            labelname.setPixmap(QPixmap(r"{}/Title.png".format(IMAGE_LOCATION)).scaled(labelwidth, labelheight, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            labelname.setPixmap(QPixmap(r"{}\Title.png".format(IMAGE_LOCATION)).scaled(labelwidth, labelheight, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        labelname.setGeometry((Window.width - labelwidth)/2, Window.height/20, labelwidth, labelheight)
    def mainstyle(self, labelname):
        """For the screen title style when there is no room for the LEGO LIGO image"""
        labelname.setGeometry(Window.width/100, Window.height/100, Window.width - Window.width/100,
                              Window.height/8)
        labelname.setStyleSheet("QLabel {color: white; font: 16pt Century Gothic}")
    def substyle(self, labelname):
        """For the screen subtitle"""
        labelname.setGeometry(Window.width/100, Window.height*1/10, Window.width - Window.width/100,
                              Window.height/4)
        labelname.setStyleSheet("QLabel {color: white; font: 12pt Century Gothic}")
    def warningstyle(self, labelname):
        """For when the mirror has moved too far"""
        labelname.setGeometry(Window.width/3, Window.height*3/10, Window.width*2/3, 2*Window.fnt12hght)
        labelname.setStyleSheet("QLabel {color: white; font: 12pt Century Gothic}")
    def homechoicestyle(self, labelname, xposition):
        """For the buttons on the home screen"""
        #scales button dimensions with window size, ensures square buttons
        labelwidth = Window.width/8
        buttonheight = Window.width/8
        ystart = Window.height*3/5
        labelxgap = Window.width/8
        labelname.setAlignment(Qt.AlignCenter)
        labelname.setGeometry((Window.width - labelwidth)/2 + labelwidth*(xposition - 2) + labelxgap*(xposition - 2),
                              ystart + buttonheight*1.2, labelwidth, Window.fnt10hght)
        labelname.setStyleSheet("QLabel {color: white; font: italic 10pt Century Gothic}")
    def movechoicestyle(self, labelname, xposition, yposition, enlarge=False):
        """Describes move choice buttons
        Set on same grid as movechoicestyle buttons
        enlarge is for the text that is larger than the buttonwidth"""
        labelwidth = Window.width/9 #as with CreateButton.style
        buttonheight = Window.width/9 #as with CreateButton.style
        labelheight = Window.fnt12hght
        labelxgap = Window.width/63
        ystart = Window.height/2
        labelygap = Window.height/20
        labelygap = Window.height/20
        labelname.setAlignment(Qt.AlignCenter)
        if enlarge is False:
            labelname.setGeometry(labelxgap*(xposition-1) + labelwidth*(xposition - 1),
                                  ystart + labelygap*(yposition-2) + buttonheight*(yposition - 1), labelwidth, labelheight)
        if enlarge is True:
            labelname.setGeometry(labelxgap*(xposition-1) + labelwidth*(xposition - 1),
                                  ystart + labelygap*(yposition-2.5) + buttonheight*(yposition - 1), labelwidth, labelheight*2)
        labelname.setStyleSheet("QLabel {color: white; font: italic 12pt Century Gothic}")
    def basestyle(self, labelname):
        labelname.setAlignment(Qt.AlignCenter)
        labelname.setGeometry(Window.width*13/63, Window.height*36/40, Window.width/3, Window.fnt10hght)
        labelname.setStyleSheet("QLabel {color: white; font: italic 10pt Century Gothic}")

def plot(self, file, clear=False):
    """Section 10: Used for plotting and 'clearing' (actually just draws over it)

    Parameters
    -----------
    file = integer, the desired files position in list of files in the folder
    clear = Boolean, used for 'clearing' the plot if required
    """
    class PlotCanvas(FigureCanvas):
        """Class for plotting the canvas"""
        def __init__(self, parent=None, width=Window.width, height=Window.height, dpi=100):
            """Sets up the canvas for plotting or 'clearing' (actually just draws over it)"""
            self.fig = Figure(figsize=((Window.width - 100)/dpi, (Window.height - Window.fnt16hght)/dpi),
                              dpi=dpi, facecolor='None')#in inches
            if RP is True:
                self.dv_data = degree_velocity(PARAMS['RPFOLDER'], files_in_folder(PARAMS['\
RPFOLDER'])[file], 'all_points')[0] #ensures only called once
            else:
                self.dv_data = degree_velocity(PARAMS['FOLDER'], files_in_folder(PARAMS['\
FOLDER'])[file], 'all_points')[0] #ensures only called once
            FigureCanvas.__init__(self, self.fig)
            self.setParent(parent)

            if clear is False:
                self.move(0, 0)
                self.plot()

            if clear is True:
                self.show()
                self.resize(Window.width, Window.height - Window.fnt16hght)
                self.move(0, 0)

        def plot(self):
            """Plots the data onto the canvas"""
            ax = self.figure.add_subplot(1, 1, 1)
            ax.set_title('Strain v Time of Mirror Movement', color='white', fontsize=18)

            ax.plot(self.dv_data[:, 0], self.dv_data[:, 5], 'r.') #Motor a, data points are red dots
            ax.set_xlabel('Time [s]', color='white', fontsize=14)
            ax.set_ylabel('Strain', color='white', fontsize=14)
            ax.tick_params(colors='white')

            self.draw()
            self.flush_events()
            self.show()
    PlotCanvas(self)

def position_tracker(mapower, matime, mbpower, mbtime):
    """Section 11: Keeps track of approximate motor positions by altering global variables MXPos and MYPos
                This is very rough and is a reason for the constant requirement of re-calibrating the motors"""
    madegree = mapower*matime*PARAMS['pwrcoef']
    mbdegree = mbpower*mbtime*PARAMS['pwrcoef']
    global MXPos
    MXPos -= madegree
    global MYPos
    MYPos -= mbdegree

def movemotor(self, file):
    """Section 12: used for providing the motor function (section 14) with the correct information
                when in preset mode.
            Takes the dv_data and iterates through to provide the motor with enough
                power and for long enough to make the necessary movement"""
    self.dv_data = degree_velocity(PARAMS['RPFOLDER'], files_in_folder(PARAMS['\
RPFOLDER'])[file], PARAMS['mode'])[0] #ensures only called once
    mapower = (self.dv_data[:, 3])/(self.dv_data[:, 4]*PARAMS['pwrcoef'])
    count = 0
    for i in mapower:
        motor(i, self.dv_data[:, 4][count], -mapower[count], self.dv_data[:, 4][count], 'preset', 'GraphUI') #dv_data[:, 4] is time_diff
        count += 1

def resetxpos():
    """Section 13.a used for returning the x mirror to its 0 position"""
    global MXPos
    if MXPos == 0:
        position_tracker(0, 0, 0, 0)
    else:
        stx = time.time()
        ti = np.abs(MXPos/(PARAMS['return_pwr']*PARAMS['pwrcoef']))
        if MXPos < 0:
            mapower = -PARAMS['return_pwr']
        elif MXPos > 0:
            mapower = PARAMS['return_pwr']
        while time.time() - stx < ti:
            BrickPi.MotorSpeed[PORT_A] = mapower
            BrickPiUpdateValues()
            while ti + PARAMS['stop_buffer'] > time.time() - stx >= ti:
                BrickPi.MotorSpeed[PORT_A] = 0 #prevents 'coasting'
                BrickPiUpdateValues()
        position_tracker(mapower, ti, 0, 0)

def resetypos():
    """Section 13.b used for returning the y mirror to its 0 position"""
    global MYPos
    if MYPos == 0:
        position_tracker(0, 0, 0, 0)
    else:
        sty = time.time()
        ti = np.abs(MYPos/(PARAMS['return_pwr']*PARAMS['pwrcoef']))
        if MYPos > 0:
            mbpower = PARAMS['return_pwr']
        elif MYPos < 0:
            mbpower = -PARAMS['return_pwr']
        while time.time() - sty < ti:
            BrickPi.MotorSpeed[PORT_B] = mbpower
            BrickPiUpdateValues()
            while ti + PARAMS['stop_buffer'] > time.time() - sty >= ti:
                BrickPi.MotorSpeed[PORT_B] = 0 #prevents 'coasting'
                BrickPiUpdateValues()
        position_tracker(0, 0, mbpower, ti)

def motor(mapower, matime, mbpower, mbtime, type, UI):
    """Section 14: used for moving the motor"""
    if type == 'MirrorXTimed':
        spa = int(round(mapower))
        position_tracker(mapower, matime, 0, 0)
        if spa < 0:
            direction = 'forward'
        elif spa > 0:
            direction = 'backward'
        if RP is True:
            runtime = np.abs(matime)
            st = time.time()
            while time.time() - st < runtime:
                UI.label.setText("Mirror X is moving {}".format(direction))
                QApplication.processEvents()
                BrickPi.MotorSpeed[PORT_A] = spa
                BrickPiUpdateValues()
                while runtime + PARAMS['stop_buffer'] > time.time() - st >= runtime:
                    BrickPi.MotorSpeed[PORT_A] = 0 #prevents 'coasting'
                    BrickPiUpdateValues()
                    UI.label.setText("Mirror X has moved {}".format(direction))

    if type == 'MirrorYTimed':
        spb = int(round(mbpower))
        position_tracker(0, 0, mbpower, mbtime)
        if spb > 0:
            direction = 'backward'
        elif spb < 0:
            direction = 'forward'
        if RP is True:
            runtime = np.abs(mbtime)
            st = time.time()
            while time.time() - st < runtime:
                UI.label.setText("Mirror X is moving {}".format(direction))
                QApplication.processEvents()
                BrickPi.MotorSpeed[PORT_B] = spb
                BrickPiUpdateValues()
                while runtime + PARAMS['stop_buffer'] > time.time() - st >= runtime:
                    BrickPi.MotorSpeed[PORT_B] = 0 #prevents 'coasting'
                    BrickPiUpdateValues()
                    UI.label.setText("Mirror Y has moved {}".format(direction))
    if type == 'preset':
        spa = int(round(mapower))
        spb = int(round(mbpower))
        position_tracker(spa, matime, spb, mbtime)
        if RP is True:
            st = time.time()
            while time.time() - st < matime:#matime and mbtime are identical
                BrickPi.MotorSpeed[PORT_A] = spa
                BrickPi.MotorSpeed[PORT_B] = spb
                BrickPiUpdateValues()
                while matime + PARAMS['stop_buffer'] > time.time() - st >= matime:
                    BrickPi.MotorSpeed[PORT_A] = 0 #prevents 'coasting'
                    BrickPi.MotorSpeed[PORT_B] = 0
                    BrickPiUpdateValues()


class WelcomeScreenUI():
    """Section 15.a: Class for describing the Welcome Screen Interface"""
    def setupui(self, mainwindow):
        """Sets up Welcome Screen Interface"""
        mainwindow.setGeometry(Window.left, Window.top, Window.width, Window.height)
        mainwindow.setWindowTitle(Window.title)
        mainwindow.statusBar().setStyleSheet("QStatusBar {color: white}")
        mainwindow.statusBar().showMessage('Welcome to Lego-LIGO')
        if RP is True:
            oimage = QImage(r"{}/Background.jpg".format(IMAGE_LOCATION))
        else:
            oimage = QImage(r"{}\Background.jpg".format(IMAGE_LOCATION))
        simage = oimage.scaled(QSize(Window.width, Window.height))# resize to widget size
        palette = QPalette()
        palette.setBrush(10, QBrush(simage))# 10 = Windowrole
        mainwindow.setPalette(palette)
        self.centralwidget = QWidget(mainwindow)

        self.sublabel = QLabel("Please begin by calibrating the mirrors.", self.centralwidget)
        CreateLabel().substyle(self.sublabel)

        self.titlelabel = QLabel(self.centralwidget)
        CreateLabel().titlestyle(self.titlelabel)

        self.nextbtn = QPushButton(self.centralwidget)
        CreateButton().nextstyle(self.nextbtn)
        self.nextbtn.setToolTip('Proceed to calibration information')

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        mainwindow.setCentralWidget(self.centralwidget)


class HomeUI():
    """Section 15.b: Class for describing the Home screen's interface"""
    def setupui(self, mainwindow):
        """Sets up Home screen interface"""
        mainwindow.statusBar().showMessage('Home')
        self.centralwidget = QWidget(mainwindow)

        self.titlelabel = QLabel(self.centralwidget)
        CreateLabel().titlestyle(self.titlelabel)

        self.selfmovementbtn = QPushButton(self.centralwidget)
        CreateButton().homechoicestyle(self.selfmovementbtn, 'Manual', 2)
        self.selfmovementlbl = QLabel('Manual', self.centralwidget)
        CreateLabel().homechoicestyle(self.selfmovementlbl, 2)

        self.calibratebtn = QPushButton(self.centralwidget)
        CreateButton().homechoicestyle(self.calibratebtn, 'Calibration', 1)
        self.calibratelbl = QLabel('Calibration', self.centralwidget)
        CreateLabel().homechoicestyle(self.calibratelbl, 1)

        self.choosemovementbtn = QPushButton(self.centralwidget)
        CreateButton().homechoicestyle(self.choosemovementbtn, 'Preset', 3)
        self.choosemovementlbl = QLabel('Preset', self.centralwidget)
        CreateLabel().homechoicestyle(self.choosemovementlbl, 3)

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        mainwindow.setCentralWidget(self.centralwidget)


class SelfMovementUI():
    """Section 15.c: Class for describing the Self Movement Screen Interface"""
    def setupui(self, mainwindow):
        """Sets up the Self Movement Interface"""
        mainwindow.statusBar().showMessage('Manual Mode')
        self.centralwidget = QWidget(mainwindow)

        if PARAMS['self_movement_run_time'] == 1:
            a = "second"
        elif PARAMS['self_movement_run_time'] != 1:
            a = "seconds"
        fast = round(PARAMS['self_movement_run_time']*PARAMS['Fast_time_multiplier'], 2)
        if fast == 1:
            b = "second"
        elif fast != 1:
            b = "seconds"

        self.mainlabel = QLabel("Welcome to Manual mode.", self.centralwidget)
        CreateLabel().mainstyle(self.mainlabel)
        self.sublabel = QLabel("Please move the mirrors using the buttons provided.\n\
The forward and backward buttons cause the motors to run for {} {}.\n\
The fast forward and fast rewind buttons cause the motors to run at {} times the speed for {}\n      {}.\
".format(PARAMS['self_movement_run_time'], a, PARAMS['Fast_power_multiplier'], fast, b), self.centralwidget)
        CreateLabel().substyle(self.sublabel)


        self.label = QLabel('', self.centralwidget)
        CreateLabel().basestyle(self.label)

        self.mxlabel = QLabel('Mirror X', self.centralwidget)
        CreateLabel().movechoicestyle(self.mxlabel, 1, 1.5)
        self.mylabel = QLabel('Mirror Y', self.centralwidget)
        CreateLabel().movechoicestyle(self.mylabel, 1, 2.5)
        self.ffdlabel = QLabel('Fast\nForward', self.centralwidget)
        CreateLabel().movechoicestyle(self.ffdlabel, 2, 1, enlarge=True)
        self.fwdlabel = QLabel('Forward', self.centralwidget)
        CreateLabel().movechoicestyle(self.fwdlabel, 3, 1)
        self.bwdlabel = QLabel('Backward', self.centralwidget)
        CreateLabel().movechoicestyle(self.bwdlabel, 4, 1)
        self.frdlabel = QLabel('Fast\nRewind', self.centralwidget)
        CreateLabel().movechoicestyle(self.frdlabel, 5, 1, enlarge=True)

        self.warninglabel = QLabel('', self.centralwidget)
        CreateLabel().warningstyle(self.warninglabel)

        self.homebtn = QPushButton("", self.centralwidget)
        CreateButton().homestyle(self.homebtn)

        self.mxffdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxffdbtn, 'Fast_Forward', 1, 1)

        self.mxfwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxfwdbtn, 'Forward', 2, 1)

        self.mxbwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxbwdbtn, 'Backward', 3, 1)

        self.mxfrdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxfrdbtn, 'Fast_Rewind', 4, 1)

        self.myffdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.myffdbtn, 'Fast_Forward', 1, 2)

        self.myfwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.myfwdbtn, 'Forward', 2, 2)

        self.mybwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mybwdbtn, 'Backward', 3, 2)

        self.myfrdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.myfrdbtn, 'Fast_Rewind', 4, 2)

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        mainwindow.setCentralWidget(self.centralwidget)


class CalibrateUI():
    """Section 15.d: Class for describing the Calibrate Screen Interface"""
    def setupui(self, mainwindow):
        """Sets up the Calibrate Interface"""
        mainwindow.statusBar().showMessage('Calibration Mode')
        self.centralwidget = QWidget(mainwindow)

        self.mainlabel = QLabel("Welcome to Calibration mode.", self.centralwidget)
        CreateLabel().mainstyle(self.mainlabel)
        if PARAMS['Calibrate_run_time'] == 1:
            a = "second"
        elif PARAMS['Calibrate_run_time'] != 1:
            a = "seconds"
        fast = round(PARAMS['Calibrate_run_time']*PARAMS['Fast_time_multiplier'], 2)
        if fast == 1:
            b = "second"
        elif fast != 1:
            b = "seconds"
        self.sublabel = QLabel("Please move the mirrors until the front, wave-carrying arm lies between the rows of red tiles.\n\
The forward and backward buttons cause the motors to run for {} {}.\nThe fast forward and fast rewind buttons cause the motors to run at {} times the speed for {}\n      {}.\
".format(PARAMS['Calibrate_run_time'], a, PARAMS['Fast_power_multiplier'], fast, b), self.centralwidget)
        CreateLabel().substyle(self.sublabel)

        self.label = QLabel('', self.centralwidget)
        CreateLabel().basestyle(self.label)

        self.mxlabel = QLabel('Mirror X', self.centralwidget)
        CreateLabel().movechoicestyle(self.mxlabel, 1, 1.5)
        self.mylabel = QLabel('Mirror Y', self.centralwidget)
        CreateLabel().movechoicestyle(self.mylabel, 1, 2.5)
        self.ffdlabel = QLabel('Fast\nForward', self.centralwidget)
        CreateLabel().movechoicestyle(self.ffdlabel, 2, 1, enlarge=True)
        self.fwdlabel = QLabel('Forward', self.centralwidget)
        CreateLabel().movechoicestyle(self.fwdlabel, 3, 1)
        self.bwdlabel = QLabel('Backward', self.centralwidget)
        CreateLabel().movechoicestyle(self.bwdlabel, 4, 1)
        self.frdlabel = QLabel('Fast\nRewind', self.centralwidget)
        CreateLabel().movechoicestyle(self.frdlabel, 5, 1, enlarge=True)

        self.homebtn = QPushButton("", self.centralwidget)
        CreateButton().homestyle(self.homebtn)
        self.homebtn.hide()

        self.setbtn = QPushButton("", self.centralwidget)
        CreateButton().tickstyle(self.setbtn)

        self.mxffdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxffdbtn, 'Fast_Forward', 1, 1)

        self.mxfwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxfwdbtn, 'Forward', 2, 1)

        self.mxbwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxbwdbtn, 'Backward', 3, 1)

        self.mxfrdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mxfrdbtn, 'Fast_Rewind', 4, 1)

        self.myffdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.myffdbtn, 'Fast_Forward', 1, 2)

        self.myfwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.myfwdbtn, 'Forward', 2, 2)

        self.mybwdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.mybwdbtn, 'Backward', 3, 2)

        self.myfrdbtn = QPushButton("", self.centralwidget)
        CreateButton().movechoicestyle(self.myfrdbtn, 'Fast_Rewind', 4, 2)

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        mainwindow.setCentralWidget(self.centralwidget)


class ChooseMovementUI(object):
    """Section 15.e: Class for describing the Choose Movement Screen Interface"""
    def setupui(self, mainwindow):
        """Sets up the Choose Movement Interface"""
        mainwindow.statusBar().showMessage('Preset Mode')
        self.centralwidget = QWidget(mainwindow)

        self.mainlabel = QLabel("Welcome to Preset mode.", self.centralwidget)
        CreateLabel().mainstyle(self.mainlabel)

        self.sublabel = QLabel("Please choose a file from the list to perform that movement.", self.centralwidget)
        CreateLabel().substyle(self.sublabel)

        self.homebtn = QPushButton("", self.centralwidget)
        CreateButton().homestyle(self.homebtn)

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        self.filebuttons = {}
        count = 1
        if RP is True:
            for i in range(len(files_in_folder(PARAMS['RPFOLDER']))):
                # keep a reference to the buttons
                self.filebuttons[i] = QPushButton('{}'.format(files_in_folder(PARAMS['\
RPFOLDER'])[i].replace(".csv", "")), self.centralwidget)
                # add to the layout
                CreateButton().namestyle(self.filebuttons[i], count)
                count += 1
                self.filebuttons[i].setStyleSheet("QPushButton {background-color: \
black; color: white}")
                self.filebuttons[i].setToolTip('Executes {} file'.format('{\
}'.format(files_in_folder(PARAMS['RPFOLDER'])[i].replace(".csv", ""))))
        else:
            for i in range(len(files_in_folder(PARAMS['FOLDER']))):
                # keep a reference to the buttons
                self.filebuttons[i] = QPushButton('{}'.format(files_in_folder(PARAMS['\
FOLDER'])[i].replace(".csv", "")), self.centralwidget)
                # add to the layout
                CreateButton().namestyle(self.filebuttons[i], count)
                count += 1
                self.filebuttons[i].setStyleSheet("QPushButton {background-color: \
black; color: white}")
                self.filebuttons[i].setToolTip('Executes {} file'.format('{\
}'.format(files_in_folder(PARAMS['FOLDER'])[i].replace(".csv", ""))))

        mainwindow.setCentralWidget(self.centralwidget)


class FileWarningUI():
    """Section 15.f Class for describing the File Warning Screen Interface"""
    def setupui(self, mainwindow):
        """Sets up the File Warning Interface"""
        mainwindow.statusBar().showMessage('Warning')
        self.centralwidget = QWidget(mainwindow)

        self.homebtn = QPushButton("", self.centralwidget)
        CreateButton().homestyle(self.homebtn)

        self.titlelabel = QLabel(self.centralwidget)
        CreateLabel().titlestyle(self.titlelabel)

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        self.label = QLabel("Warning: There are too many '.csv' files in the folder.\
\n              The maximum number of '.csv' files allowed is 10.\
\n              To enter preset mode please close \
the program, reduce the number of '.csv' files in \
\n                  the folder and then restart the program.\
\n              For other options press the 'Home' button.", self.centralwidget)
        self.label.setGeometry(Window.width/100, Window.height - Window.height/3,
                               Window.width - Window.width/100, Window.height/5)
        self.label.setStyleSheet("QLabel {color: white; font-size: 12pt}")

        mainwindow.setCentralWidget(self.centralwidget)


class SpeedWarningUI():
    """Section 15.g: Class for describing the Speed Warning Screen Interface"""
    def setupui(self, mainwindow):
        """Sets up the Speed Warning Interface"""
        mainwindow.statusBar().showMessage('Warning')
        self.centralwidget = QWidget(mainwindow)

        self.homebtn = QPushButton(self.centralwidget)
        CreateButton().homestyle(self.homebtn)

        self.titlelabel = QLabel(self.centralwidget)
        CreateLabel().titlestyle(self.titlelabel)

        self.exitbtn = QPushButton(self.centralwidget)
        CreateButton().exitstyle(self.exitbtn)

        self.label = QLabel("Warning: The motor cannot achieve the required speed.\
\n              Please adjust the time scale.\
\n              For other options press the 'Home' button", self.centralwidget)
        self.label.setGeometry(Window.width/100, Window.height - Window.height/3,
                               Window.width - Window.width/100, Window.height/5)
        self.label.setStyleSheet("QLabel {color: white; font-size: 12pt}")

        mainwindow.setCentralWidget(self.centralwidget)


class MainWindow(QMainWindow):
    """Section 16: Class for calling all of the various user interfaces"""
    def __init__(self, parent=None):
        """Calls the various interfaces"""
        super(MainWindow, self).__init__(parent)
        self.setParent(parent)
        self.uihome = HomeUI()
        self.uiselfmovement = SelfMovementUI()
        self.uicalibrate = CalibrateUI()
        self.uichoosemovement = ChooseMovementUI()
        self.uifilewarning = FileWarningUI()
        self.uispeedwarning = SpeedWarningUI()
        self.uiwelcomescreen = WelcomeScreenUI()
        self.startWelcomeScreenUI()

    def motorcheck(self, UI):
        global MXPos
        global MYPos
        limit = PARAMS['degree_max']*PARAMS['manualbuffer']
        if MXPos >= limit or MXPos <= -limit:
            UI.warninglabel.setText("Warning: Mirror has reached limit\nThe mirrors will now return to their default positions.")
            resetxpos()
        else:
            UI.warninglabel.setText("")
        if MYPos >= limit or MYPos <= -limit:
            UI.warninglabel.setText("Warning: Mirror has reached limit\nThe mirrors will now return to their default positions.")
            resetypos()
        else:
            UI.warninglabel.setText("")

    def MXFfdSelfMovement(self):
        motor(-PARAMS['self_movement_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['self_movement_run_time']*PARAMS['Fast_time_multiplier'], 0, 0, 'MirrorXTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MXFwdSelfMovement(self):
        motor(-PARAMS['self_movement_pwr'], PARAMS['self_movement_run_time'], 0, 0, 'MirrorXTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MXBwdSelfMovement(self):
        motor(PARAMS['self_movement_pwr'], PARAMS['self_movement_run_time'], 0, 0, 'MirrorXTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MXFrdSelfMovement(self):
        motor(PARAMS['self_movement_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['self_movement_run_time']*PARAMS['Fast_time_multiplier'], 0, 0, 'MirrorXTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MYFfdSelfMovement(self):
        motor(0, 0, -PARAMS['self_movement_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['self_movement_run_time']*PARAMS['Fast_time_multiplier'], 'MirrorYTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MYFwdSelfMovement(self):
        motor(0, 0, -PARAMS['self_movement_pwr'], PARAMS['self_movement_run_time'], 'MirrorYTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MYBwdSelfMovement(self):
        motor(0, 0, PARAMS['self_movement_pwr'], PARAMS['self_movement_run_time'], 'MirrorYTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def MYFrdSelfMovement(self):
        motor(0, 0, PARAMS['self_movement_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['self_movement_run_time']*PARAMS['Fast_time_multiplier'], 'MirrorYTimed', self.uiselfmovement)
        self.motorcheck(self.uiselfmovement)

    def SetCalibrate(self):
        global MXPos
        global MYPos
        MXPos = 0
        MYPos = 0
        self.uicalibrate.label.setText("Calibration has been set")

    def MXFfdCalibrate(self):
        motor(-PARAMS['Calibrate_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['Calibrate_run_time']*PARAMS['Fast_time_multiplier'], 0, 0, 'MirrorXTimed', self.uicalibrate)

    def MXFwdCalibrate(self):
        motor(-PARAMS['Calibrate_pwr'], PARAMS['Calibrate_run_time'], 0, 0, 'MirrorXTimed', self.uicalibrate)

    def MXBwdCalibrate(self):
        motor(PARAMS['Calibrate_pwr'], PARAMS['Calibrate_run_time'], 0, 0, 'MirrorXTimed', self.uicalibrate)

    def MXFrdCalibrate(self):
        motor(PARAMS['Calibrate_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['Calibrate_run_time']*PARAMS['Fast_time_multiplier'], 0, 0, 'MirrorXTimed', self.uicalibrate)

    def MYFfdCalibrate(self):
        self.uicalibrate.label.setText("Mirror Y is moving forward")
        motor(0, 0, -PARAMS['Calibrate_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['Calibrate_run_time']*PARAMS['Fast_time_multiplier'], 'MirrorYTimed', self.uicalibrate)

    def MYFwdCalibrate(self):
        motor(0, 0, -PARAMS['Calibrate_pwr'], PARAMS['Calibrate_run_time'], 'MirrorYTimed', self.uicalibrate)

    def MYBwdCalibrate(self):
        motor(0, 0, PARAMS['Calibrate_pwr'], PARAMS['Calibrate_run_time'], 'MirrorYTimed', self.uicalibrate)

    def MYFrdCalibrate(self):
        motor(0, 0, PARAMS['Calibrate_pwr']*PARAMS['Fast_power_multiplier'], PARAMS['Calibrate_run_time']*PARAMS['Fast_time_multiplier'], 'MirrorYTimed', self.uicalibrate)

    def file0caller(self):
        self.startGraphUI(0)
    def file1caller(self):
        self.startGraphUI(1)
    def file2caller(self):
        self.startGraphUI(2)
    def file3caller(self):
        self.startGraphUI(3)
    def file4caller(self):
        self.startGraphUI(4)
    def file5caller(self):
        self.startGraphUI(5)
    def file6caller(self):
        self.startGraphUI(6)
    def file7caller(self):
        self.startGraphUI(7)
    def file8caller(self):
        self.startGraphUI(8)
    def file9caller(self):
        self.startGraphUI(9)
    def file10caller(self):
        self.startGraphUI(10)
    def file11caller(self):
        self.startGraphUI(11)
    def file12caller(self):
        self.startGraphUI(12)

    def closeit(self):
        self.close()

    def starthomeUI(self):
        self.uihome.setupui(self)
        self.uihome.selfmovementbtn.clicked.connect(self.startSelfMovementUI)
        self.uihome.calibratebtn.clicked.connect(self.startCalibrateUI)
        self.uihome.choosemovementbtn.clicked.connect(self.startChooseMovementUI)
        self.uihome.exitbtn.clicked.connect(self.closeit)
        self.show()

    def startWelcomeScreenUI(self):
        self.uiwelcomescreen.setupui(self)
        self.uiwelcomescreen.nextbtn.clicked.connect(self.startCalibrateUI)
        self.uiwelcomescreen.exitbtn.clicked.connect(self.closeit)
        self.show()

    def startSelfMovementUI(self):
        self.uiselfmovement.setupui(self)
        self.uiselfmovement.homebtn.clicked.connect(self.starthomeUI)
        self.uiselfmovement.mxffdbtn.clicked.connect(self.MXFfdSelfMovement)
        self.uiselfmovement.mxfwdbtn.clicked.connect(self.MXFwdSelfMovement)
        self.uiselfmovement.mxbwdbtn.clicked.connect(self.MXBwdSelfMovement)
        self.uiselfmovement.mxfrdbtn.clicked.connect(self.MXFrdSelfMovement)
        self.uiselfmovement.myffdbtn.clicked.connect(self.MYFfdSelfMovement)
        self.uiselfmovement.myfwdbtn.clicked.connect(self.MYFwdSelfMovement)
        self.uiselfmovement.mybwdbtn.clicked.connect(self.MYBwdSelfMovement)
        self.uiselfmovement.myfrdbtn.clicked.connect(self.MYFrdSelfMovement)
        self.uiselfmovement.exitbtn.clicked.connect(self.closeit)
        self.show()

    def startCalibrateUI(self):
        self.uicalibrate.setupui(self)
        self.uicalibrate.homebtn.clicked.connect(self.starthomeUI)
        self.uicalibrate.setbtn.clicked.connect(self.SetCalibrate)
        self.uicalibrate.setbtn.clicked.connect(self.showhomebtn)
        self.uicalibrate.mxffdbtn.clicked.connect(self.MXFfdCalibrate)
        self.uicalibrate.mxfwdbtn.clicked.connect(self.MXFwdCalibrate)
        self.uicalibrate.mxbwdbtn.clicked.connect(self.MXBwdCalibrate)
        self.uicalibrate.mxfrdbtn.clicked.connect(self.MXFrdCalibrate)
        self.uicalibrate.myffdbtn.clicked.connect(self.MYFfdCalibrate)
        self.uicalibrate.myfwdbtn.clicked.connect(self.MYFwdCalibrate)
        self.uicalibrate.mybwdbtn.clicked.connect(self.MYBwdCalibrate)
        self.uicalibrate.myfrdbtn.clicked.connect(self.MYFrdCalibrate)
        self.uicalibrate.exitbtn.clicked.connect(self.closeit)
        self.show()
    def showhomebtn(self):
        self.uicalibrate.homebtn.show()
    def startFileWarningUI(self):
        self.uifilewarning.setupui(self)
        self.uifilewarning.homebtn.clicked.connect(self.starthomeUI)
        self.uifilewarning.exitbtn.clicked.connect(self.closeit)
        self.show()

    def startSpeedWarningUI(self):
        self.uispeedwarning.setupui(self)
        self.uispeedwarning.homebtn.clicked.connect(self.starthomeUI)
        self.uispeedwarning.exitbtn.clicked.connect(self.closeit)
        self.show()


    def startChooseMovementUI(self):
        if RP is True:
            self.statusBar().showMessage('Returning motors to default position')
            QApplication.processEvents()
            resetxpos()
            resetypos()
            self.statusBar().showMessage('Choose a Movement Mode')
            QApplication.processEvents()
            if len(files_in_folder(PARAMS['RPFOLDER'])) >= 11:
                self.startFileWarningUI()
            elif len(files_in_folder(PARAMS['RPFOLDER'])) < 11:
                self.uichoosemovement.setupui(self)
                self.uichoosemovement.homebtn.clicked.connect(self.starthomeUI)
                self.uichoosemovement.exitbtn.clicked.connect(self.closeit)
                for i in range(len(files_in_folder(PARAMS['RPFOLDER']))):
                    cmd = "self.uichoosemovement.filebuttons[%d].clicked.connect(self.file%dcaller)"%(i, i)
                    exec(cmd)
        else:
            if len(files_in_folder(PARAMS['FOLDER'])) >= 11:
                self.startFileWarningUI()
            elif len(files_in_folder(PARAMS['FOLDER'])) < 11:
                self.uichoosemovement.setupui(self)
                self.uichoosemovement.homebtn.clicked.connect(self.starthomeUI)
                self.uichoosemovement.exitbtn.clicked.connect(self.closeit)
                for i in range(len(files_in_folder(PARAMS['FOLDER']))):
                    cmd = "self.uichoosemovement.filebuttons[%d].clicked.connect(self.file%dcaller)"%(i, i)
                    exec(cmd)
        self.show()

    def clearGraphUI(self):
        plot(self, 0, clear=True) #0 simply fills in the file parameter
        self.starthomeUI()

    def startGraphUI(self, file):
        if RP is True:
            if degree_velocity(PARAMS['RPFOLDER'], files_in_folder(PARAMS['RPFOLDER'])[file], 'warning_check')[1] == True:
                self.startSpeedWarningUI()
            elif degree_velocity(PARAMS['RPFOLDER'], files_in_folder(PARAMS['RPFOLDER'])[file], 'warning_check')[1] == False:
                self.setGeometry(Window.left, Window.top, Window.width, Window.height)
                self.setWindowTitle(Window.title)

                plot(self, file)

                self.statusBar().showMessage('Performing {}'.format(files_in_folder(PARAMS['RPFOLDER'])[file].replace('.csv', '')))
                self.centralwidget = QWidget(self)
                self.setCentralWidget(self.centralwidget)

                self.homebtn = QPushButton(self.centralwidget)
                CreateButton().homestyle(self.homebtn)
                self.homebtn.clicked.connect(self.clearGraphUI)
                self.exitbtn = QPushButton(self.centralwidget)
                CreateButton().exitstyle(self.exitbtn)
                self.exitbtn.clicked.connect(self.closeit)
                QApplication.processEvents()
                movemotor(self, file)
                sleep(2)
                self.statusBar().showMessage('Returning motors to default position')
                QApplication.processEvents()
                resetxpos()
                resetypos()
        else:
            if degree_velocity(PARAMS['FOLDER'], files_in_folder(PARAMS['FOLDER'])[file], 'warning_check')[1] == True:
                self.startSpeedWarningUI()
            elif degree_velocity(PARAMS['FOLDER'], files_in_folder(PARAMS['FOLDER'])[file], 'warning_check')[1] == False:
                self.setGeometry(Window.left, Window.top, Window.width, Window.height)
                self.setWindowTitle(Window.title)
                plot(self, file)

                self.statusBar().showMessage('Performing {}'.format(files_in_folder(PARAMS['FOLDER'])[file].replace('.csv', '')))
                self.centralwidget = QWidget(self)
                self.setCentralWidget(self.centralwidget)

                self.homebtn = QPushButton(self.centralwidget)
                CreateButton().homestyle(self.homebtn)
                self.homebtn.clicked.connect(self.clearGraphUI)
                self.exitbtn = QPushButton(self.centralwidget)
                CreateButton().exitstyle(self.exitbtn)
                self.exitbtn.clicked.connect(self.closeit)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
