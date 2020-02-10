import pandas as pd
import math
import numpy as np
from Experiment.EyeMovement import EyeMovement
from Experiment.Fixation import Fixation
from Experiment.Saccade import Saccade
from Experiment.Coordinate import Coordinate

class ParserEyeMovement:

    def __init__(self, data, durationThreshold, angleThreshold):
        """

        :param data: dataframe
        :param durationThreshold: in ms
        :param angleThreshold: in degrees
        """
        self.data = data
        self.durationThreshold = durationThreshold
        self.angleTrheshold = angleThreshold

    def createEyeMovements(self):
        df = self.data
        vectors = calculateVectors(df)
        distance = calculateDistance(vectors)
        valid = selectValidPoints(distance)
        eyemovements = findFixations(valid, self.durationThreshold, self.angleTrheshold)
        return eyemovements


def calculateVectors(df):
    df['vector'] = df.apply(lambda row: getVector(row), axis=1)
    df['vectorNext'] = df['vector'].shift(periods=-1)
    df['vectorNext'].iloc[-1] = df['vectorNext'].iloc[-2]
    return df


def calculateDistance(df):
    '''
    Calculates distance in mm
    :param df:
    :return:
    '''
    df['distance'] = df.apply(lambda row: getDistance(row), axis=1)
    return df


def getVector(row):
    return [
        row['xO'] - row['x3'],
        row['yO'] - row['y3'],
        row['zO'] - row['z3']
    ]


def getDistance(row):
    dx = row['xO'] - row['x3']
    dy = row['yO'] - row['y3']
    dz = row['zO'] - row['z3']
    dX = dx **2
    dY = dy **2
    dZ = dz **2
    totDelta = dX + dY + dZ
    return math.sqrt(totDelta)


def selectValidPoints(df):
    return df.loc[(df['x'] > 0) & (df['y'] > 0)]


def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)


def angle_between(v1, v2):
    """ Returns the angle in radians between vectors 'v1' and 'v2'
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


def findDispersion(df, index):
    """
    Find the dispersion in the df
    :param df:
    :param index:
    :return:
    """
    minX = df['x'].idxmin()
    maxX = df['x'].idxmax()
    minY = df['y'].min()
    maxY = df['y'].max()
    deltaX = abs(maxX - minX)
    deltaY = abs(maxY - minY)
    if index == 0:
        return deltaX
    else:
        return deltaY


def findAverage(df):
    """
    Calculate the mean of 3 columns
    :param df:
    :return:
    """
    x = df['x3'].mean()
    y = df['y3'].mean()
    z = df['z3'].mean()
    return [x, y, z]


def checkDispersion(df, x, y, z, threshold):
    """
    Check if dispersion angle is above a threshold
    Look for average point of df
    Search biggest angle between eye-middle and eye-df
    Check if largest angle is above threshold/2
    :param df:
    :param x:
    :param y:
    :param z:
    :param threshold:
    :return:
    """
    [ x1, y1, z1] = findAverage(df)
    vectorAverage = [x - x1, y- y1, z - z1]
    angle = 0
    length = len(df.index)
    for i in range(0, length):
        x3 = df['x3'].iloc[i]
        y3 = df['y3'].iloc[i]
        z3 = df['z3'].iloc[i]
        vector = [x - x3, y - y3, z - z3]
        angleI = math.degrees(angle_between(vectorAverage, vector))
        if angleI > angle:
            angle = angleI
    # as we take the angle to the middle, use the helft of threshold
    if angle > (threshold/2):
        return False
    else:
        return True



def findFixations(df, durationThreshold, angleThreshold):
        # Loop over file
        durationFix = 2
        durationSac = 2
        start = 0
        length = len(df.index)
        eyeMovements = []
        for i in range(0, length):
            window = df.iloc[start:start + durationFix]
            oX = df.iloc[start]['xO']
            oY = df.iloc[start]['yO']
            oZ = df.iloc[start]['zO']

            # Check if all points in window are within limits
            dispersion = checkDispersion(window, oX, oY, oZ, angleThreshold)
            if dispersion:
                durationFix += 1
            else:
                startTimeFix = df['system_time_stamp'].iloc[start]
                endTimeFix = df['system_time_stamp'].iloc[start + durationFix - 1]
                durationFixation = endTimeFix - startTimeFix
                if durationFixation > durationThreshold:

                    # append saccade
                    startTimeSac = df['system_time_stamp'].iloc[start-durationSac]
                    endTimeSac = df['system_time_stamp'].iloc[start-1]

                    startLocationXSac = df['x'].iloc[start-durationSac]
                    startLocationYSac = df['y'].iloc[start-durationSac]
                    endLocationXSac = df['x'].iloc[start-1]
                    endLocationYSac = df['y'].iloc[start-1]

                    startLocationSac = Coordinate(startLocationXSac, startLocationYSac)
                    endLocationSac = Coordinate(endLocationXSac, endLocationYSac)

                    saccade = Saccade(startLocationSac, endLocationSac, startTimeSac, endTimeSac)
                    eyeMovements.append(saccade)

                    # append fixation
                    startTimeFix = df['system_time_stamp'].iloc[start]
                    endTimeFix = df['system_time_stamp'].iloc[start + durationFix - 1]
                    fixX = window['x'].mean()
                    fixY = window['y'].mean()
                    fix = Coordinate(fixX, fixY)

                    fixation = Fixation(fix, startTimeFix, endTimeFix, durationThreshold, angleThreshold )
                    eyeMovements.append(fixation)

                    # reset window and durations
                    start = i
                    durationFix = 2
                    durationSac = 2

                else:
                    durationFix = 2
                    durationSac += 1
                    start = i
        return eyeMovements